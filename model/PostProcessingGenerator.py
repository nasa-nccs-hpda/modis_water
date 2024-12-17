from osgeo import gdal
import numpy as np
from pathlib import Path

from modis_water.model.BandReader import BandReader
from modis_water.model.Utils import Utils
from modis_water.model.ImperviousMap import ImperviousMap


# -------------------------------------------------------------------------
# PostProcessingMap
# -------------------------------------------------------------------------
class PostProcessingMap(object):

    IN_DTYPE: np.dtype = np.uint8
    OUT_DTYPE: np.dtype = np.uint16
    NCOLS: int = 4800
    NROWS: int = 4800

    DESCRIPTION: str = 'MOD44W post-processing packed bit mask'

    DEM_SLOPE_CUTOFF: int = 5

    TIF_BASE_NAME = 'Master_7class_maxextent_'

    ANCILLARY_PRE_STR: str = 'Dyn_Water_Ancillary_'
    ANCILLARY_POST_STR: str = '*.tif'
    PERMANENT_WATER_PRE_STR: str = 'Water.'
    PERMANENT_WATER_POST_STR: str = '*.tif'

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

    ANC_WATER_VALUE: int = 1
    ANC_LAND_VALUE: int = 0
    ANC_OCEAN_VALUE: int = 2
    ANC_FILL_VALUE: int = 9
    ANC_NODATA_VALUE: int = 10

    ANCILLARY_BIT_MASK_DICT: dict = {
        ANC_LAND_VALUE: ANC_LAND_BIT_MASK,
        ANC_WATER_VALUE: ANC_WATER_BIT_MASK,
        ANC_OCEAN_VALUE: ANC_OCEAN_BIT_MASK,
        ANC_NODATA_VALUE: ANC_NODATA_BIT_MASK
    }

    # Seven Class Mask
    SC_SHALLOW_BIT_MASK: int = 128  # 0b10000000
    SC_LAND_BIT_MASK: int = 256  # 0b100000000
    SC_PL0_BIT_MASK: int = 512  # 0b1000000000
    SC_INLAND_BIT_MASK: int = 1024  # 0b10000000000
    SC_PL1_BIT_MASK: int = 2048  # 0b100000000000
    SC_DIN_BIT_MASK: int = 4096  # 0b1000000000000
    SC_MOC_BIT_MASK: int = 8192  # 0b10000000000000
    SC_DOC_BIT_MASK: int = 16384  # 0b100000000000000
    SC_NODATA_BIT_MASK: int = 32640  # 0b111111110000000

    SC_SHALLOW_VALUE: int = 0
    SC_LAND_VALUE: int = 1
    SC_PL0_VALUE: int = 2
    SC_INLAND_VALUE: int = 3
    SC_PL1_VALUE: int = 4
    SC_DEEP_INLAND_VALUE: int = 5
    SC_MODERATE_OCEAN_VALUE: int = 6
    SC_DEEP_OCEAN_VALUE: int = 7
    SC_NODATA_VALUE: int = 253

    SEVEN_CLASS_BIT_MASK_DICT: dict = {
        SC_SHALLOW_VALUE: SC_SHALLOW_BIT_MASK,
        SC_LAND_VALUE: SC_LAND_BIT_MASK,
        SC_PL0_VALUE: SC_PL0_BIT_MASK,
        SC_INLAND_VALUE: SC_INLAND_BIT_MASK,
        SC_PL1_VALUE: SC_PL1_BIT_MASK,
        SC_DEEP_INLAND_VALUE: SC_DIN_BIT_MASK,
        SC_MODERATE_OCEAN_VALUE: SC_MOC_BIT_MASK,
        SC_DEEP_OCEAN_VALUE: SC_DOC_BIT_MASK,
        SC_NODATA_VALUE: SC_NODATA_BIT_MASK
    }

    # Out-of-projection Mask
    OOP_BIT_MASK: int = 32768  # 0b1000000000000000
    OOP_VALUE: int = 250

    def __init__(self,
                 tile: str,
                 outDir: str,
                 imperviousDir: str,
                 permanentWaterDir: str,
                 gmtedDir: str,
                 ancillaryDir: str,
                 sevenClassDir: str) -> None:
        """
        Initialize the PostProcessingMap with the required tile and directory paths.  # noqa: E501

        Args:
            tile (str): The identifier for the tile to be processed.
            imperviousDir (str): Directory path for impervious data.
            permanentWaterDir (str): Directory path for permanent water data.
            gmtedDir (str): Directory path for GMTED data.
            ancillaryMaskDir (str): Directory path for ancillary mask data.
            sevenClassDir (str): Directory path for seven-class data.
        """
        self.tile = tile
        self.outDir: Path = Path(outDir)
        self.imperviousDir: Path = Path(imperviousDir)
        self.permanentWaterDir: Path = Path(permanentWaterDir)
        self.gmtedDir: Path = Path(gmtedDir)
        self.ancillaryDir: Path = Path(ancillaryDir)
        self.sevenClassDir: Path = Path(sevenClassDir)

        self.exclusionTile = self.tile[3:] in Utils.QA_ANTARCTIC_EXCLUSION

    # -------------------------------------------------------------------------
    # generatePostProcessingMask
    # -------------------------------------------------------------------------
    def generatePostProcessingMask(self) -> None:

        # Read in ancillary data files for processing.
        demArray = self._getGMTEDArray()
        permArray = self._getPermanentWaterArray()
        sevenClassArray, outputMetadata = self._getStaticSevenClassArray(
            returnMetadata=True)
        ancillaryArray = self._getAncillaryArray(sevenClassArray)
        imperviousArray = ImperviousMap.generateImperviousBinaryMask(
            self.tile, self.imperviousDir)

        # Process all the arrays into the packed bit array
        packedBitPostProcessingMask = np.zeros(
            (BandReader.COLS, BandReader.ROWS),
            dtype=PostProcessingMap.OUT_DTYPE)

        # ---
        # Start processing of binary arrays.
        # These are simple, just shift the binary value to the correct it location.  # noqa: E501
        # ---

        # Process binaryimpervious surface ancillary mask.
        imperviousPosBinArray = self._generatePositionalBinaryArray(
            imperviousArray, PostProcessingMap.IMPERVIOUS_BIT_MASK)
        packedBitPostProcessingMask = \
            (packedBitPostProcessingMask | imperviousPosBinArray)

        # Process binary permanent water ancillary mask.
        permanentPosBinArray = self._generatePositionalBinaryArray(
            permArray, PostProcessingMap.PERMANENT_BIT_MASK)
        packedBitPostProcessingMask = \
            (packedBitPostProcessingMask | permanentPosBinArray)

        # Generate binary GMTED DEM mask, then process.
        demBinaryArray = self._generateDEMPositionalBinaryArray(
            demArray,
            sevenClassArray,
            ancillaryArray)

        demPosBinArray = self._generatePositionalBinaryArray(
            demBinaryArray, PostProcessingMap.GMTED_BIT_MASK)
        packedBitPostProcessingMask = \
            (packedBitPostProcessingMask | demPosBinArray)

        # ---
        # Start processing of multi-value arrays.
        # These are a bit more complex as we have to cycle through and isolate
        # the value we want to shift to the specified bit location.
        # ---

        # Process multi-value ancillary mask.
        packedBitPostProcessingMask = \
            self._addAncillaryToPackedBits(
                ancillaryArray,
                packedBitPostProcessingMask)

        # Process multi-value seven-class mask.
        packedBitPostProcessingMask = \
            self._addSevenClassToPackedBits(
                sevenClassArray,
                packedBitPostProcessingMask)

        # Process multi-value Out-Of-Projection mask.
        packedBitPostProcessingMask = \
            self._addOutOfProjectionPackedBits(
                sevenClassArray,
                packedBitPostProcessingMask)

        self._writePackedBitRaster(packedBitPostProcessingMask,
                                   outputMetadata)

    # -------------------------------------------------------------------------
    # _generateDEMPositionalBinaryArray
    # -------------------------------------------------------------------------
    def _generateDEMPositionalBinaryArray(
            self,
            demArray: np.ndarray,
            sevenClassArray: np.ndarray,
            ancillaryArray: np.ndarray) -> np.ndarray:

        demBinary = np.where(
            demArray > PostProcessingMap.DEM_SLOPE_CUTOFF, 1, 0)
        demOceanFlip = (demBinary & (
            (sevenClassArray != PostProcessingMap.SC_LAND_VALUE) |
            (ancillaryArray != PostProcessingMap.ANC_WATER_VALUE)))
        demBinary = np.where(demOceanFlip, 0, demBinary)
        return demBinary

    # -------------------------------------------------------------------------
    # _generatePositionalBinaryArray
    # -------------------------------------------------------------------------
    def _generatePositionalBinaryArray(
            self, binaryArray: np.ndarray, bitMask: int) -> np.ndarray:

        positionalBinary = np.where(binaryArray == 1, bitMask, 0)

        return positionalBinary

    # -------------------------------------------------------------------------
    # _addAncillaryToPackedBits
    # -------------------------------------------------------------------------
    def _addAncillaryToPackedBits(
            self,
            ancillaryArray: np.ndarray,
            postProcessingMask: np.ndarray) -> np.ndarray:

        ancillaryBitMaskDict = PostProcessingMap.ANCILLARY_BIT_MASK_DICT

        for ancillaryValue in ancillaryBitMaskDict.keys():
            positionalBinary = np.where(
                ancillaryArray == ancillaryValue,
                ancillaryBitMaskDict[ancillaryValue], 0)
            postProcessingMask = (postProcessingMask | positionalBinary)

        return postProcessingMask

    # -------------------------------------------------------------------------
    # _addSevenClassToPackedBits
    # -------------------------------------------------------------------------
    def _addSevenClassToPackedBits(
            self,
            sevenClassArray: np.ndarray,
            postProcessingMask: np.ndarray) -> np.ndarray:

        scBitMaskDict = PostProcessingMap.SEVEN_CLASS_BIT_MASK_DICT
        for scValue in scBitMaskDict.keys():
            positionalBinary = np.where(
                sevenClassArray == scValue, scBitMaskDict[scValue], 0)
            postProcessingMask = (postProcessingMask | positionalBinary)
        return postProcessingMask

    # -------------------------------------------------------------------------
    # _addOutOfProjectionPackedBits
    # -------------------------------------------------------------------------
    def _addOutOfProjectionPackedBits(
            self,
            sevenClassArray: np.ndarray,
            postProcessingMask: np.ndarray) -> np.ndarray:

        oopBitMask = PostProcessingMap.OOP_BIT_MASK
        oopValue = PostProcessingMap.OOP_VALUE
        positionalBinary = np.where(sevenClassArray == oopValue, oopBitMask, 0)
        postProcessingMask = (postProcessingMask | positionalBinary)

        return postProcessingMask

    # -------------------------------------------------------------------------
    # _getGMTEDArray
    # -------------------------------------------------------------------------
    def _getGMTEDArray(self) -> np.ndarray:

        try:
            demSearchTerm = 'GMTED.{}.slope.tif'.format(self.tile)
            demSlopeDatasetPath = Utils.getStaticDatasetPath(
                self.gmtedDir, demSearchTerm)
            demSlopeDataset = gdal.Open(demSlopeDatasetPath)
            demSlopeDataArray = demSlopeDataset.GetRasterBand(
                1).ReadAsArray()
        except FileNotFoundError as initialException:
            if self.exclusionTile:
                demSlopeDataArray = np.zeros(
                    (BandReader.COLS, BandReader.ROWS),
                    dtype=PostProcessingMap.IN_DTYPE)
            else:
                raise initialException
        return demSlopeDataArray

    # -------------------------------------------------------------------------
    # _getAncillaryArray
    # -------------------------------------------------------------------------
    def _getAncillaryArray(self, sevenClassArray: np.ndarray) -> np.ndarray:
        try:
            ancillarySearchTerm = \
                f'{PostProcessingMap.ANCILLARY_PRE_STR}{self.tile}' + \
                f'{PostProcessingMap.ANCILLARY_POST_STR}'
            ancillaryDatasetPath = Utils.getStaticDatasetPath(
                self.ancillaryDir, ancillarySearchTerm)
            ancillaryDataset = gdal.Open(ancillaryDatasetPath)
            ancillaryDataArray = ancillaryDataset.GetRasterBand(
                1).ReadAsArray()
        except FileNotFoundError as initialException:
            if self.exclusionTile:
                ancillaryDataArray = self._generateAntarcticAncillaryMask(
                    sevenClassArray)
            else:
                raise initialException
        return ancillaryDataArray

    # -------------------------------------------------------------------------
    # _getAncillaryArray
    # -------------------------------------------------------------------------
    def _getPermanentWaterArray(self) -> np.ndarray:
        permanentWaterSearchTerm = \
            PostProcessingMap.PERMANENT_WATER_PRE_STR + \
            self.tile + \
            PostProcessingMap.PERMANENT_WATER_POST_STR
        permanentWaterDatasetPath = Utils.getStaticDatasetPath(
            self.permanentWaterDir, permanentWaterSearchTerm)
        permanentWaterDataset = gdal.Open(permanentWaterDatasetPath)
        permanentWaterDataArray = permanentWaterDataset.GetRasterBand(
            1).ReadAsArray()
        return permanentWaterDataArray

    # -------------------------------------------------------------------------
    # _getStaticSevenClassPath
    # -------------------------------------------------------------------------
    def _getStaticSevenClassArray(self,
                                  returnMetadata: bool = False) -> np.ndarray:
        staticSevenClassSearchTerm = '{}{}.tif'.format(
            PostProcessingMap.TIF_BASE_NAME, self.tile)
        staticSevenClassDatasetPath = Utils.getStaticDatasetPath(
            self.sevenClassDir, staticSevenClassSearchTerm
        )
        sevenClassDataset = gdal.Open(str(staticSevenClassDatasetPath))
        sevenClassDataArray = sevenClassDataset.GetRasterBand(1).ReadAsArray()
        if returnMetadata:
            transform = sevenClassDataset.GetGeoTransform()
            projection = sevenClassDataset.GetProjection()
            return sevenClassDataArray, (transform, projection)
        return sevenClassDataArray

    # -------------------------------------------------------------------------
    # _generateAntarcticAncillaryMask
    # -------------------------------------------------------------------------
    def _generateAntarcticAncillaryMask(self, staticSevenClass: np.ndarray):
        antarcticAncillaryMask = np.zeros((4800, 4800)).astype(np.uint8)
        antarcticAncillaryMask.fill(self.ANC_FILL_VALUE)

        oopBool = (staticSevenClass == PostProcessingMap.SC_NODATA_VALUE)

        oceanBool = \
            (staticSevenClass ==
             PostProcessingMap.SC_SHALLOW_VALUE) | \
            (staticSevenClass ==
             PostProcessingMap.SC_MODERATE_OCEAN_VALUE) | \
            (staticSevenClass == PostProcessingMap.SC_DEEP_OCEAN_VALUE)

        antarcticAncillaryMask = np.where(oopBool,
                                          PostProcessingMap.ANC_NODATA_VALUE,
                                          antarcticAncillaryMask)

        antarcticAncillaryMask = np.where(oceanBool,
                                          PostProcessingMap.ANC_OCEAN_VALUE,
                                          antarcticAncillaryMask)

        return antarcticAncillaryMask

    # -------------------------------------------------------------------------
    # _writePackedBitRaster
    # -------------------------------------------------------------------------
    def _writePackedBitRaster(
            self, packedBitArray: np.ndarray, outputMetadata: tuple) -> None:
        cols = packedBitArray.shape[0]
        rows = packedBitArray.shape[1] if len(packedBitArray.shape) > 1 else 1
        packedBitName = f'postprocess_water_{self.tile}.tif'
        packedBitPath = self.outDir / packedBitName
        driver = gdal.GetDriverByName('GTiff')
        transform, projection = outputMetadata

        ds = driver.Create(str(packedBitPath), cols, rows, 1, gdal.GDT_UInt16,
                           options=['COMPRESS=LZW'])
        ds.SetProjection(projection)
        ds.SetGeoTransform(transform)
        band = ds.GetRasterBand(1)
        band.SetNoDataValue(250)
        band.SetDescription(PostProcessingMap.DESCRIPTION)
        band.WriteArray(packedBitArray, 0, 0)
        band = None
        ds = None
