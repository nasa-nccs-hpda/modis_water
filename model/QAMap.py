import os
import logging

from osgeo import gdal
import rasterio as rio
import numpy as np

from modis_water.model.BandReader import BandReader
from modis_water.model.Utils import Utils


"""
QA LEGEND

Legend=
    1: High Confidence Observation
    2: Low Confidence Water, but MOD44W C5 is water
    3: Low Confidence Land
    4: Ocean Mask
    5: Ocean Mask but no water detected
    6: Burn Scar (from MCD64A1)
    7: Urban/Impervious surface
    8: No water detected, Collection 5 shows water
    9: DEM Slope change
    10: No data (outside of projected area)

ANCILLARY MASK LEGEND

Legend=
    0: possible water (max extent)
    1: land
    2: ocean
    9: fill value
    10: outside projection
"""


# -------------------------------------------------------------------------
# QAMap
# -------------------------------------------------------------------------
class QAMap(object):

    DTYPE: np.dtype = np.uint8
    NCOLS: int = 4800
    NROWS: int = 4800

    ANNUAL_WATER: int = 1
    ANNUAL_LAND: int = 0
    ANNUAL_OUT_OF_PROJECTION: int = 250
    ANCILLARY_WATER: int = 0
    ANCILLARY_LAND: int = 1
    ANCILLARY_OCEAN: int = 2
    PERMANENT_WATER_WATER: int = 1

    QA_HIGH_CONFIDENCE: int = 1
    QA_LOW_CONFIDENCE: int = 2
    QA_LOW_CONFIDENCE_LAND: int = 3
    QA_OCEAN: int = 4
    QA_OCEAN_NO_WATER: int = 5
    QA_BURN_SCAR: int = 6
    QA_IMPERVIOUS: int = 7
    QA_DEM_SLOPE: int = 9
    QA_NO_DATA: int = 10
    QA_OUT_OF_PROJECTION: int = 10

    BURN_SCAR: int = 1
    IMPERVIOUS_SURFACE: int = 1
    DEM_SLOPE: int = 1

    ANCILLARY_PRE_STR: str = 'Dyn_Water_Ancillary_'
    ANCILLARY_POST_STR: str = '_v3b.tif'
    TOTAL_WATER_POST_STR: str = 'SumWater.tif'
    TOTAL_LAND_POST_STR: str = 'SumLand.tif'
    PROBABILITY_WATER_POST_STR: str = 'ProbWater'
    PERMANENT_WATER_PRE_STR: str = 'Water.'
    PERMANENT_WATER_POST_STR: str = '.tif'

    # Impervious Mask
    IMPERVIOUS_BIT_MASK: int = 1

    # Permanent Water Mask
    PERMANENT_BIT_MASK: int = 2

    # GMTED Slope Mask
    GMTED_BIT_MASK: int = 4

    # Ancillary Mask
    ANC_LAND_BIT_MASK: int = 8  # 0b1000
    ANC_WATER_BIT_MASK: int = 16  # 0b10000
    ANC_OCEAN_BIT_MASK: int = 32  # 0b100000
    ANC_NODATA_BIT_MASK: int = 64  # 0b1000000

    ANC_LAND_VALUE: int = 0
    ANC_WATER_VALUE: int = 1
    ANC_OCEAN_VALUE: int = 2
    ANC_FILL_VALUE: int = 9
    ANC_NODATA_VALUE: int = 10

    ANCILLARY_BIT_MASK_DICT: dict = {
        ANC_LAND_VALUE: ANC_LAND_BIT_MASK,
        ANC_WATER_VALUE: ANC_WATER_BIT_MASK,
        ANC_OCEAN_VALUE: ANC_OCEAN_BIT_MASK,
        ANC_NODATA_VALUE: ANC_NODATA_BIT_MASK
    }

    OOP_BIT_MASK: int = 32768  # 0b1000000000000000

    # -------------------------------------------------------------------------
    # generateSevenClass
    # -------------------------------------------------------------------------
    @staticmethod
    def generateQA(
            sensor,
            year,
            tile,
            burnedAreaPath,
            postProcessingDir,
            annualProductPath,
            classifierName,
            outDir,
            logger,
            geoTiff=False,
            georeferenced=False) -> str:

        # Search for, read in our post processing rasters.
        postProcessingArray = QAMap._getPostProcessingMask(tile,
                                                           postProcessingDir)

        demSlopeDataArray = QAMap._extractPackedBitBinaryArray(
            postProcessingArray,
            QAMap.GMTED_BIT_MASK)

        imperviousDataArray = QAMap._extractPackedBitBinaryArray(
            postProcessingArray,
            QAMap.IMPERVIOUS_BIT_MASK)

        permanentWaterArray = QAMap._extractPackedBitBinaryArray(
            postProcessingArray,
            QAMap.PERMANENT_BIT_MASK)

        ancillaryDataArray = \
            QAMap._extractAncillaryArray(postProcessingArray)

        """
        totalWater = QAMap._getAnnualStatPath(
            year,
            tile,
            sensor,
            classifierName,
            QAMap.TOTAL_WATER_POST_STR,
            outDir)
        totalLand = QAMap._getAnnualStatPath(
            year,
            tile,
            sensor,
            classifierName,
            QAMap.TOTAL_LAND_POST_STR,
            outDir)
        """

        annualProductDataset = gdal.Open(annualProductPath)
        annualProductArray = annualProductDataset.GetRasterBand(
            1).ReadAsArray()

        totalLand = np.where(annualProductArray == 0, 100, 0)
        totalWater = np.where(annualProductArray == 1, 100, 0)

        burnScarArray = QAMap._readAndResample(burnedAreaPath)

        annualProductOutput = annualProductArray.copy()
        qaOutput = np.zeros(annualProductArray.shape, dtype=QAMap.DTYPE)

        # QA Map Case 2, MODIS_water_algorithm_MODIS_v2 1.d.ii.2
        low_confidence_water = (
            (permanentWaterArray == QAMap.PERMANENT_WATER_WATER) &
            (totalWater >= 3) &
            (ancillaryDataArray != QAMap.ANCILLARY_LAND))
        qaOutput = np.where(low_confidence_water,
                            QAMap.QA_LOW_CONFIDENCE,
                            qaOutput)

        # QA MAP Case 1, MODIS_water_algorithm_MODIS_v2 1.d.ii.3
        high_confidence_water = (
            (annualProductArray == QAMap.ANNUAL_WATER) &
            (totalWater >= 6) &
            (ancillaryDataArray != QAMap.ANCILLARY_LAND))
        qaOutput = np.where(high_confidence_water,
                            QAMap.QA_HIGH_CONFIDENCE,
                            qaOutput)

        # QA Map Case 4, MODIS_water_algorithm_MODIS_v2 1.d.ii.4
        ocean_mask = (ancillaryDataArray == QAMap.ANCILLARY_OCEAN)
        qaOutput = np.where(ocean_mask,
                            QAMap.QA_OCEAN,
                            qaOutput)

        annualProductOutput = np.where(
            (low_confidence_water | high_confidence_water | ocean_mask),
            QAMap.ANNUAL_WATER,
            annualProductOutput)

        # QA Map Case 6, MODIS_water_algorithm_MODIS_v2 1.d.iii.1-2
        burn_scar_case = (burnScarArray == QAMap.BURN_SCAR)
        annualProductOutput = np.where(
            burn_scar_case, QAMap.ANNUAL_LAND, annualProductOutput)
        qaOutput = np.where(burn_scar_case,
                            QAMap.QA_BURN_SCAR,
                            qaOutput)

        # Burn scar flip back
        burn_scar_water_max_extent = (
            (burnScarArray == QAMap.BURN_SCAR) &
            (annualProductArray == QAMap.ANNUAL_WATER) &
            (ancillaryDataArray == QAMap.ANCILLARY_WATER))
        annualProductOutput = np.where(
            burn_scar_water_max_extent,
            QAMap.ANNUAL_WATER,
            annualProductOutput)

        # QA Map Case 9
        dem_slope_case = (demSlopeDataArray == QAMap.DEM_SLOPE) & \
            (annualProductArray == QAMap.ANNUAL_WATER)
        annualProductOutput = np.where(
            dem_slope_case, QAMap.ANNUAL_LAND, annualProductOutput)
        qaOutput = np.where(dem_slope_case,
                            QAMap.QA_DEM_SLOPE,
                            qaOutput)

        # QA map case 5, MODIS_water_algorithm_MODIS_v2 1.d.iv.1
        ocean_mask_no_water = ((annualProductArray == QAMap.ANNUAL_WATER) & (
            totalWater < 3) & (ancillaryDataArray == QAMap.ANCILLARY_OCEAN))
        qaOutput = np.where(ocean_mask_no_water,
                            QAMap.QA_OCEAN_NO_WATER,
                            qaOutput)

        # QA map case 3, MODIS_water_algorithm_MODIS_v2 1.d.iv.2
        low_confidence_land = (
            (annualProductArray == QAMap.ANNUAL_LAND) &
            (totalLand < 6) &
            (ancillaryDataArray != QAMap.ANCILLARY_OCEAN) &
            (annualProductOutput != QAMap.ANNUAL_WATER) &
            (qaOutput != QAMap.QA_DEM_SLOPE) &
            (qaOutput != QAMap.QA_BURN_SCAR))
        qaOutput = np.where(low_confidence_land,
                            QAMap.QA_LOW_CONFIDENCE_LAND,
                            qaOutput)

        # High confidence land flip back
        high_confidence_land = (ancillaryDataArray == QAMap.ANCILLARY_LAND)
        annualProductOutput = np.where(
            high_confidence_land,
            QAMap.ANNUAL_LAND,
            annualProductOutput)

        # QA map case 7, MODIS_water_algorithm_MODIS_v2 1.d.v.5-6
        impervious_case = ((imperviousDataArray == QAMap.IMPERVIOUS_SURFACE) &
                           (annualProductOutput == QAMap.ANNUAL_WATER) &
                           (ancillaryDataArray == QAMap.ANCILLARY_WATER))
        qaOutput = np.where(impervious_case, QAMap.QA_IMPERVIOUS, qaOutput)
        annualProductOutput = np.where(impervious_case, 0, annualProductOutput)

        # QA map case 10, MODIS_water_algorithm_MODIS_v2 1.d.vi.1-2
        out_of_projection = (postProcessingArray &
                             QAMap.ANC_NODATA_BIT_MASK) \
            == QAMap.ANC_NODATA_BIT_MASK

        annualProductOutput = np.where(
            out_of_projection,
            QAMap.ANNUAL_OUT_OF_PROJECTION,
            annualProductOutput)
        qaOutput = np.where(out_of_projection,
                            QAMap.QA_OUT_OF_PROJECTION,
                            qaOutput)

        # Write out the final annual product in addition to the QA map.
        annualProductOutputName = \
            '{}44W.A{}.{}.{}.AnnualWaterProduct.{}'.format(
                sensor, year, tile, classifierName, Utils.getPostStr())
        qaOutputName = '{}44W.A{}.{}.{}.AnnualWaterProductQA.{}'.format(
            sensor, year, tile, classifierName, Utils.getPostStr())

        transform = annualProductDataset.GetGeoTransform() \
            if georeferenced else None
        projection = annualProductDataset.GetProjection() \
            if georeferenced else None

        annualPath = QAMap._writeProduct(
            outDir,
            annualProductOutputName,
            annualProductOutput,
            logger=logger,
            projection=projection,
            transform=transform,
            geoTiff=geoTiff)

        QAMap._writeProduct(outDir,
                            qaOutputName,
                            qaOutput,
                            logger=logger,
                            projection=projection,
                            transform=transform,
                            geoTiff=geoTiff)

        return annualPath

    # -------------------------------------------------------------------------
    # _getPostProcessingMask
    # -------------------------------------------------------------------------
    @staticmethod
    def _getPostProcessingMask(tile: str, postProcessingDir: str) \
            -> np.ndarray:
        postProcessingSearchTerm = 'postprocess_water_{}.tif'.format(tile)
        postProcessingDatasetPath = Utils.getStaticDatasetPath(
            postProcessingDir, postProcessingSearchTerm)
        postProcessingDataset = gdal.Open(postProcessingDatasetPath)
        postProcessingDataArray = postProcessingDataset.GetRasterBand(
            1).ReadAsArray()
        return postProcessingDataArray

    # -------------------------------------------------------------------------
    # _extractAncillaryArray
    # -------------------------------------------------------------------------
    @staticmethod
    def _extractAncillaryArray(postProcessingMask: np.ndarray) -> np.ndarray:
        ancillaryBitMaskDict = QAMap.ANCILLARY_BIT_MASK_DICT
        ancillaryDataArray = np.zeros(
            (BandReader.COLS, BandReader.ROWS), dtype=QAMap.DTYPE)
        ancillaryDataArray.fill(QAMap.ANC_FILL_VALUE)
        for ancillaryValue in ancillaryBitMaskDict.keys():
            bitMask = ancillaryBitMaskDict[ancillaryValue]
            condition = (postProcessingMask & bitMask) == bitMask
            ancillaryDataArray = np.where(condition, ancillaryValue,
                                          ancillaryDataArray)
        return ancillaryDataArray

    # -------------------------------------------------------------------------
    # _extractPackedBitBinaryArray
    # -------------------------------------------------------------------------
    @staticmethod
    def _extractPackedBitBinaryArray(postProcessingMask: np.ndarray,
                                     bitMask: int) -> np.ndarray:
        extractedBinaryArray = np.where((postProcessingMask &
                                         bitMask) == bitMask, 1, 0)
        return extractedBinaryArray.astype(QAMap.DTYPE)

    # -------------------------------------------------------------------------
    # _getAnnualStatPath
    # -------------------------------------------------------------------------
    @staticmethod
    def _getAnnualStatPath(
            year: int, tile: str, sensor: str,
            classifierName: str, postFix: str, outputDir: str) -> np.ndarray:
        name = Utils.getImageName(year,
                                  tile,
                                  sensor,
                                  classifierName,
                                  None,
                                  postFix)
        statPath = Utils.getStaticDatasetPath(outputDir, name)
        try:
            statDataset = gdal.Open(statPath)
            statDataArray = statDataset.GetRasterBand(
                1).ReadAsArray()
        except RuntimeError as e:
            msg = f'{str(e)}: Encountered error while trying to open' + \
                f' {statPath} with GDAL.'
            raise RuntimeError(msg)
        return statDataArray

    # -------------------------------------------------------------------------
    # _readAndResample
    # -------------------------------------------------------------------------
    @staticmethod
    def _readAndResample(filepath: str, bandNum: int = 1) -> np.ndarray:
        outShape = (BandReader.COLS, BandReader.ROWS)
        resamplingMethod = rio.enums.Resampling(2)
        with rio.open(filepath) as dataset:
            band = dataset.read(bandNum, out_shape=outShape,
                                resampling=resamplingMethod)
        return band

    # -------------------------------------------------------------------------
    # writeProduct
    # -------------------------------------------------------------------------
    @staticmethod
    def _writeProduct(outDir: str, outName: str,
                      array: np.ndarray, logger: logging.Logger,
                      projection: str, transform: str,
                      geoTiff: bool = False) -> str:
        cols = array.shape[0]
        rows = array.shape[1] if len(
            array.shape) > 1 else 1
        fileType = '.tif' if geoTiff else '.bin'
        imageName = os.path.join(outDir, outName + fileType)
        driver = gdal.GetDriverByName('GTiff') if geoTiff \
            else gdal.GetDriverByName('ENVI')
        options = ['COMPRESS=LZW'] if geoTiff else []
        ds = driver.Create(imageName, cols, rows, 1, gdal.GDT_Byte,
                           options=options)
        if projection:
            ds.SetProjection(projection)
        if transform:
            ds.SetGeoTransform(transform)

        band = ds.GetRasterBand(1)
        band.WriteArray(array, 0, 0)
        band = None
        ds = None
        if logger:
            logger.info('Wrote annual QA products to: {}'.format(imageName))
        return imageName
