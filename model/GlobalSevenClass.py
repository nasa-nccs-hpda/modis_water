import logging
import os
import pathlib
import tempfile
from tqdm import tqdm

from numba import njit
import numpy as np

from osgeo import gdal
from osgeo.osr import SpatialReference
from skimage.segmentation import find_boundaries
from skimage.util import apply_parallel


from core.model.SystemCommand import SystemCommand
from modis_water.model.SevenClass import SevenClassMap
from modis_water.model.QAMap import QAMap

os.environ['USE_PYGEOS'] = '0'


# -----------------------------------------------------------------------------
# class GlobalSevenClassMap
# -----------------------------------------------------------------------------
class GlobalSevenClassMap(object):
    """
    Generates a global mosaic of the MOD44W seven class product.
    """

    LAT_LON_EPSG: str = "EPSG:4326"

    HDF_SUBDATASET_PRE_STR: str = 'HDF4_EOS:EOS_GRID:"'

    HDF_SEVENCLASS_POST_STR: str = '":MOD44W_250m_GRID:seven_class'

    # ---
    # Excude the PEP rules violation of going past 80 chars -
    # this thing is a mess if it is broken up into subcomponents.
    # ---
    MODIS_SINUSOIDAL_6842_PROJ_STR: str = 'PROJCS["Sinusoidal",GEOGCS["GCS_Undefined",DATUM["Undefined",SPHEROID["User_Defined_Spheroid",6371007.181,0.0]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]],PROJECTION["Sinusoidal"],PARAMETER["False_Easting",0.0],PARAMETER["False_Northing",0.0],PARAMETER["Central_Meridian",0.0],UNIT["Meter",1.0]]'

    MODIS_SINUSOIDAL_6842 = SpatialReference(MODIS_SINUSOIDAL_6842_PROJ_STR)

    # The 7-class value which indicates shoreline
    SHORELINE_VAL: int = 2

    # The 7-class value which indicates land
    LAND_VAL: int = 1

    SC_NODATA: int = 250

    SC_DTYPE: np.dtype = np.uint8

    # Constants for applying seven class global product to generate shoreline
    PARALLEL_GRID_SIZE: int = 1020

    PARALLEL_OVERLAP: int = 64

    PARALLEL_MODE: str = 'reflect'

    ANTARCTIC_EXCLUSION: list = ['v17', 'v16', 'v15', 'v14']

    # ---
    # The first 4 bits of the anc mask are reserved for 7-class values
    # to add to the final mask where the origianl 7-class is no-data
    # ---
    SEVEN_CLASS_RESERVED_BITS: int = 0b1111

    # ---
    # This bit is reserved for cases where anc pixels should be used
    # instead of the 7-class values. This is for cases where we know
    # the 7-class is wrong, e.g. edges of the dateline where reprojection
    # artifacts pop up.
    # ---
    CORRECTIVE_BIT_MASK: int = 0b1110000

    OCEAN_SET: list = [0, 6, 7]

    REPLACEMENT_VALUE: int = 0

    NUM_INLAND_OC_ADJ_ITERS: int = 10

    # -------------------------------------------------------------------------
    # __init__
    # -------------------------------------------------------------------------
    def __init__(self,
                 hdfDirectory: str,
                 ancFilePath: str,
                 postProcessingDir: str,
                 year: int, sensor,
                 outputDir: str,
                 logger: logging.Logger,
                 debug: bool = False) -> None:

        self.hdfDirectory = pathlib.Path(hdfDirectory)
        self.validateFileExists(self.hdfDirectory)

        self.ancFilePath = pathlib.Path(ancFilePath)
        self.validateFileExists(self.ancFilePath)

        self.postProcessingDir = pathlib.Path(postProcessingDir)
        self.validateFileExists(self.postProcessingDir)

        self._outDir = pathlib.Path(outputDir)
        self.validateFileExists(self._outDir)

        self._year = year

        self._sensor = sensor

        self._logger = logger

        self._debug = debug

        if self._debug:
            self._logger.debug(self.hdfDirectory)
            self._logger.debug(self.ancFilePath)
            self._logger.debug(self._outDir)
            self._logger.debug(self._year)
            self._logger.debug(self._sensor)

    # -------------------------------------------------------------------------
    # generateGlobalSevenClass
    # -------------------------------------------------------------------------
    def generateGlobalSevenClass(self) -> None:
        """
        Generates the global seven class product from MOD44W hdfs generated
        by MODAPS.
        """

        sevenClassNoShorelineProducts = \
            self._extractSevenClassFromHdfAndWriteWithNoShoreline()

        # Global no-shoreline in sinusoidal projection path
        globalNoShorePathSinu = self._buildOutputGlobalName(
            sevenClassNoShorelineProducts[0], wgs84=False)

        # Global no-shoreline in wgs84 projection path
        globalNoShorePathWgs84 = self._buildOutputGlobalName(
            sevenClassNoShorelineProducts[0], wgs84=True
        )

        # Write out vrt in sinu projection
        if globalNoShorePathSinu.exists():

            infoMsg = f'{globalNoShorePathSinu} exists.' + \
                ' Using for global shoreline generation.'

            self._logger.info(infoMsg)

        else:

            infoMsg = f'Writing {globalNoShorePathSinu}.'

            self._logger.info(infoMsg)

            # Build the vrt from the individual seven-class tiles
            sevenClassGlobalVrt = self._buildSevenClassVRT(
                sevenClassNoShorelineProducts)

            # Write out the VRT to disk
            self._warpAndWriteSinu(sevenClassGlobalVrt,
                                   globalNoShorePathSinu)

        # Warp sinu global product to wgs84
        if globalNoShorePathWgs84.exists():

            infoMsg = f'{globalNoShorePathWgs84} exists.' + \
                ' Using for global shoreline generation.'

            self._logger.info(infoMsg)

        else:

            infoMsg = f'Writing {globalNoShorePathWgs84}.'

            self._logger.info(infoMsg)

            # Reproject sinu proj to wgs84
            self._warpAndWriteWgs84(globalNoShorePathSinu,
                                    globalNoShorePathWgs84)

        globalNoShoreArrayMasked = self._applyCorrectingMask(
            globalNoShorePathWgs84)

        self._generateGlobalWithShoreline(globalNoShoreArrayMasked,
                                          globalNoShorePathWgs84)

    # -------------------------------------------------------------------------
    # _extractSevenClassFromHdfAndWriteWithNoShoreline
    # -------------------------------------------------------------------------
    def _extractSevenClassFromHdfAndWriteWithNoShoreline(self) -> list:
        """
        This function starts the process of reverting the shoreline on the
        per-tile level. It will return a list of paths to the written
        GeoTiff which is the seven class without shoreline.

        Returns:
            list: list of paths
        """

        hdfFilePattern = f'{self._sensor}*{self._year}*.hdf'

        if self._debug:
            self._logger.debug(hdfFilePattern)

        hdfProducts = self._getSevenClassProducts(pattern=hdfFilePattern)

        sevenClassNoShorelineProducts = []

        for hdfProduct in tqdm(hdfProducts,
                               ascii=True):

            sevenClassNoShorelinePath = self._revertShorelineAndWrite(
                hdfProduct)

            sevenClassNoShorelineProducts.append(sevenClassNoShorelinePath)

        self._validateNumberOfNoShorelineProducts(
            sevenClassNoShorelineProducts)

        return sevenClassNoShorelineProducts

    # -------------------------------------------------------------------------
    # _getSevenClassProducts
    # -------------------------------------------------------------------------
    def _getSevenClassProducts(self, pattern: str = '*.hdf') -> list:
        """
        Given a pattern, runs a function to get all the matching HDF files.
        """

        hdfProducts = list(self._getAllHdfProducts(pattern))

        if self._debug:
            self._logger.debug(hdfProducts)

        return hdfProducts

    # -------------------------------------------------------------------------
    # _getAllHdfProducts
    # -------------------------------------------------------------------------
    def _getAllHdfProducts(self, pattern: str) -> list:
        """
        Globs the HDF directory for files matching a pattern given as
        an argument.
        """
        filesMatchingPattern = self.hdfDirectory.glob(pattern)

        if self._debug:
            self._logger.debug(filesMatchingPattern)

        return filesMatchingPattern

    # -------------------------------------------------------------------------
    # _reprojectAddShoreline
    # -------------------------------------------------------------------------
    def _revertShorelineAndWrite(self, hdfProduct: pathlib.Path) -> str:
        """
        This function runs functions that gets the seven class subdataset,
        reverts the shoreline of that array and writes it to disk.
        """

        sevenClassNoShorelinePath = self._outDir / \
            hdfProduct.name.replace('.hdf', '.NoShoreline.tif')

        if self._debug:
            self._logger.debug(sevenClassNoShorelinePath)

        if sevenClassNoShorelinePath.exists():
            self._logger.info(
                f'{sevenClassNoShorelinePath} already exists.')

            return sevenClassNoShorelinePath

        # Get the original subdataset product.
        sevenClassDataset = self._getSevenClassSubDataset(
            hdfProduct)

        # Get all the attributes of the SC dataset (including array).
        sevenClassDatasetAttributes = self._getRasterAndAttributes(
            sevenClassDataset)

        if self._debug:
            self._logger.debug(sevenClassDatasetAttributes)

        del sevenClassDataset

        # ---
        # Get tile-ID from the HDF file name
        # Ex: MOD44W.A2022001.h09v05.061.2024008133218.hdf, h09v05
        # ---
        tile = hdfProduct.name.split('.')[2]

        if self._debug:
            self._logger.debug(tile)

        # If antarctic tile, mask dynamic product with static (in place)
        if tile[3:] in self.ANTARCTIC_EXCLUSION:
            if self._debug:
                self._logger.debug(f'Tile {tile} in Antarctica, masking')
            self._maskAntarcticTile(tile, sevenClassDatasetAttributes)

        # Revert the shoreline, write to an in-memory dataset.
        sevenClassNoShoreArray = self._revertShoreline(
            sevenClassDatasetAttributes)

        self._writeRevertedShoreline(
            sevenClassNoShorelinePath,
            sevenClassNoShoreArray,
            sevenClassDatasetAttributes)

        return sevenClassNoShorelinePath

    # -------------------------------------------------------------------------
    # _maskAntarcticTile
    # -------------------------------------------------------------------------
    def _maskAntarcticTile(self, tile: str,
                           sevenClassDatasetAttributes: dict) -> None:
        """
        This function converts the predicted seven class for an antarctic tile
        and masks with the static seven class map.
        """

        postProcessingArray = QAMap._getPostProcessingMask(
            tile,
            self.postProcessingDir)

        staticSevenArray = SevenClassMap._extractSevenClassArray(
            postProcessingArray, tile)

        sevenClassDatasetAttributes['ndarray'] = staticSevenArray

        np.testing.assert_equal(sevenClassDatasetAttributes['ndarray'],
                                staticSevenArray)

    # -------------------------------------------------------------------------
    # _getSevenClassSubDataset
    # -------------------------------------------------------------------------
    def _getSevenClassSubDataset(self, inputFilePath: pathlib.Path) -> \
            gdal.Dataset:
        """
        Gets the seven-class subdataset from the HDF.
        """

        sevenDatasetPath = f'{self.HDF_SUBDATASET_PRE_STR}{inputFilePath}' + \
            f'{self.HDF_SEVENCLASS_POST_STR}'

        if self._debug:
            self._logger.debug(sevenDatasetPath)

        mod44wHDFDataset = gdal.Open(sevenDatasetPath, gdal.GA_ReadOnly)

        return mod44wHDFDataset

    # -------------------------------------------------------------------------
    # _getRasterAndAttributes
    # -------------------------------------------------------------------------
    def _getRasterAndAttributes(self, sevenClassDataset: gdal.Dataset) -> dict:
        """
        Given a gdal dataset, build an attributes dictionary that includes
        information and attributes useful to working with a raster.
        """

        sevenClassRasterAttributes = {}

        sevenClassRasterAttributes['ds_metadata'] = \
            sevenClassDataset.GetMetadata()

        sevenClassRasterAttributes['projection'] = \
            sevenClassDataset.GetProjection()

        sevenClassRasterAttributes['transform'] = \
            sevenClassDataset.GetGeoTransform()

        sevenClassBand = sevenClassDataset.GetRasterBand(1)

        sevenClassRasterAttributes['ndarray'] = \
            sevenClassBand.ReadAsArray()

        sevenClassRasterAttributes['band_metadata'] = \
            sevenClassBand.GetMetadata()

        sevenClassRasterAttributes['band_description'] = \
            sevenClassBand.GetDescription()

        if self._debug:
            self._logger.debug(sevenClassRasterAttributes)

        del sevenClassDataset

        return sevenClassRasterAttributes

    # -------------------------------------------------------------------------
    # _revertWriteToMemory
    # -------------------------------------------------------------------------
    def _revertShoreline(self, sevenClassAttributesDict: dict) -> \
            np.ndarray:
        """
        Given that seven class attributes dict, this class reverts
        the shoreline of the SC array.
        """

        array = sevenClassAttributesDict['ndarray']

        sevenClassNoShoreline = GlobalSevenClassMap.revertShorelineFromArray(
            array)

        return sevenClassNoShoreline

    # -------------------------------------------------------------------------
    # revertShoreline
    # -------------------------------------------------------------------------
    @staticmethod
    def revertShorelineFromArray(arrayWithShoreline: np.ndarray) -> np.ndarray:
        """This function reverts the shoreline of a seven-class array to land.

        Args:
            arrayWithShoreline (np.ndarray):
                seven-class array with shorelines

        Returns:
            np.ndarray: seven-class array without shorelines
        """
        arrayWithOutShoreline = np.where(
            arrayWithShoreline == GlobalSevenClassMap.SHORELINE_VAL,
            GlobalSevenClassMap.LAND_VAL,
            arrayWithShoreline)

        return arrayWithOutShoreline

    # -------------------------------------------------------------------------
    # _writeRevertedShoreline
    # -------------------------------------------------------------------------
    def _writeRevertedShoreline(
            self,
            sevenClassNoShorePath: pathlib.Path,
            sevenClassNoShoreline: np.ndarray,
            originalRasterAttributeDict: dict) -> None:
        """
        Writes out a raster of the seven-class without shorelines.
        """

        # Write out the SC with shorelines
        driver = gdal.GetDriverByName('GTiff')

        rows, cols = sevenClassNoShoreline.shape

        transform = originalRasterAttributeDict['transform']

        datasetMeta = originalRasterAttributeDict['ds_metadata']

        datasetMeta['_FillValue'] = self.SC_NODATA

        bandMeta = originalRasterAttributeDict['band_metadata']

        bandDescription = originalRasterAttributeDict['band_description']

        ds = driver.Create(str(sevenClassNoShorePath), cols, rows,
                           1, gdal.GDT_Byte, options=['COMPRESS=LZW'])

        ds.SetMetadata(datasetMeta)

        ds.SetGeoTransform(transform)

        ds.SetProjection(self.MODIS_SINUSOIDAL_6842_PROJ_STR)

        ds.SetSpatialRef(self.MODIS_SINUSOIDAL_6842)

        band = ds.GetRasterBand(1)

        band.WriteArray(sevenClassNoShoreline, 0, 0)

        band.FlushCache()

        band.SetNoDataValue(self.SC_NODATA)

        band.SetMetadata(bandMeta)

        band.SetDescription(bandDescription)

        del ds

    # -------------------------------------------------------------------------
    # _validateNumberOfNoShorelineProducts
    # -------------------------------------------------------------------------
    def _validateNumberOfNoShorelineProducts(
            self,
            noShorelineProducts: list) -> bool:
        """
        Checks to make sure all 318 seven-class files were processed.
        """

        numNoShorelineProducts = len(noShorelineProducts)

        if self._debug:
            self._logger.debug(f'Num reprojected: {numNoShorelineProducts}')

        if numNoShorelineProducts < 318:

            errorMsg = 'Expected 318 seven-class files,' + \
                f' got {numNoShorelineProducts}'

            raise RuntimeError(errorMsg)

        return True

    # -------------------------------------------------------------------------
    # _buildOutputGlobalName
    # -------------------------------------------------------------------------
    def _buildOutputGlobalName(
            self,
            sevenClassSamplePath: pathlib.Path,
            wgs84: bool = False) -> pathlib.Path:
        """
        Builds the output global seven-class without shoreline raster path.
        """

        sevenClassSampleName = sevenClassSamplePath.stem

        nameSplitNoTile = sevenClassSampleName.split('.')[:2] + \
            sevenClassSampleName.split('.')[3:]

        nameNoTile = '.'.join(nameSplitNoTile)

        proj = 'wgs84' if wgs84 else 'sinu'

        finalName = nameNoTile.replace(
            'NoShoreline',
            f'AnnualSevenClass.NoShoreline.global.{proj}')

        finalSevenClassGlobalPath = self._outDir / f'{finalName}.tif'

        if self._debug:
            self._logger.debug(finalSevenClassGlobalPath)

        return finalSevenClassGlobalPath

    # -------------------------------------------------------------------------
    # _buildSevenClassVRT
    # -------------------------------------------------------------------------
    def _buildSevenClassVRT(self, sevenClassNoShorelineProducts: list) \
            -> gdal.Dataset:
        """
        Given a list of SC products, creates a VRT of those rasters.
        """

        tempDir = pathlib.Path(tempfile.gettempdir())

        sevenClassNoShorelineProductsStrPaths = \
            [str(path) for path in sevenClassNoShorelineProducts]

        vrtFilePath = tempDir / 'sevenClassNoShoreMerged.vrt'

        if vrtFilePath.exists():

            self._logger.info(f'{vrtFilePath} exists. Deleting.')

            vrtFilePath.unlink()

        if self._debug:
            self._logger.info(vrtFilePath)
            self._logger.info(sevenClassNoShorelineProductsStrPaths)

        sevenClassGlobalVrt = gdal.BuildVRT(
            str(vrtFilePath), sevenClassNoShorelineProductsStrPaths)

        return sevenClassGlobalVrt

    # -------------------------------------------------------------------------
    # _warpAndWrite
    # -------------------------------------------------------------------------
    def _warpAndWriteSinu(self,
                          sevenClassGlobalVrt,
                          outputSevenClassGlobalPath: pathlib.Path) -> None:
        """
        Given a VRT, runs gdal warp to write out the VRT to disk in sinu proj.
        """

        warpOptions = gdal.WarpOptions(
            gdal.ParseCommandLine("-of Gtiff -co COMPRESS=LZW"))

        self._logger.info(f'Warping VRT to disk with {warpOptions}')

        try:

            gdal.Warp(str(outputSevenClassGlobalPath),
                      sevenClassGlobalVrt,
                      options=warpOptions)

        except Exception as e:

            errorMsg = 'Encountered error while warping' + \
                f' global VRT. \n Error: {e}'

            raise RuntimeError(errorMsg)

    # -------------------------------------------------------------------------
    # _warpAndWriteWgs84
    # -------------------------------------------------------------------------
    def _warpAndWriteWgs84(self,
                           inputSevenClassGlobalPath: pathlib.Path,
                           outputSevenClassGlobalPath: pathlib.Path) -> None:
        """
        Reprojects the global seven-class (no shoreline) from sinu to wgs84.
        """

        warpCmd = 'gdalwarp -of GTiff -co COMPRESS=LZW -t_srs EPSG:4326'

        warpCmd = warpCmd + f' {inputSevenClassGlobalPath}' + \
            f' {outputSevenClassGlobalPath}'

        self._logger.info(f'Running: {warpCmd}')

        try:

            SystemCommand(warpCmd, logger=self._logger)

        except Exception as e:

            errorMsg = 'Encountered error while warping' + \
                f' global VRT. \n Error: {e}'

            raise RuntimeError(errorMsg)

    # -------------------------------------------------------------------------
    # _applyCorrectingMask
    # -------------------------------------------------------------------------
    def _applyCorrectingMask(self, globalNoShorePath: pathlib.Path) \
            -> None:
        """
        Given a global SC product with no shoreline, applies a corrective mask
        which fixes reprojection artifacts seen to be present in the
        reprojected product.
        """

        # Open and get attributes of the reprojected product
        globalSevenClassNoShoreline = gdal.Open(str(globalNoShorePath),
                                                gdal.GA_ReadOnly)

        globalSevenClassNoShorelineAttributes = self._getRasterAndAttributes(
            globalSevenClassNoShoreline)

        if self._debug:
            self._logger.debug(globalSevenClassNoShorelineAttributes)

        globalSevenClassNoShorelineArray = \
            globalSevenClassNoShorelineAttributes['ndarray'].astype(
                self.SC_DTYPE)

        # Open and get attributes of the corrective mask
        correctiveMask = gdal.Open(str(self.ancFilePath),
                                   gdal.GA_ReadOnly)

        correctiveMaskAttributes = self._getRasterAndAttributes(
            correctiveMask)

        if self._debug:
            self._logger.debug(correctiveMaskAttributes)

        correctiveMaskArray = \
            correctiveMaskAttributes['ndarray'].astype(
                self.SC_DTYPE)

        # START OCEAN FILL FIXING
        oceanFillMask = correctiveMaskArray & \
            GlobalSevenClassMap.SEVEN_CLASS_RESERVED_BITS

        # Any pixels where global SC is no-data and corrective mask exists
        oceanFillConditional = (globalSevenClassNoShorelineArray ==
                                self.SC_NODATA)

        if self._debug:
            self._logger.debug('Ocean fill mask attrs')
            self._logger.debug(
                f'\tOcean fills: {np.count_nonzero(oceanFillConditional)}')

        # Where above conditional, use anc mask values instead of global SC
        globalSCArrayCorrected = np.where(oceanFillConditional,
                                          oceanFillMask,
                                          globalSevenClassNoShorelineArray)

        del oceanFillConditional
        # END OCEAN FILL FIXING

        # START EDGE FIXING
        correctiveMaskSevenClass = (
            correctiveMaskArray & GlobalSevenClassMap.CORRECTIVE_BIT_MASK) >> 4

        if self._debug:
            self._logger.debug('Corrective seven class mask attrs')
            self._logger.debug(f'\tMax: {correctiveMaskSevenClass.max()}')
            self._logger.debug(f'\tMin: {correctiveMaskSevenClass.min()}')

        globalSCArrayCorrected = np.where(correctiveMaskSevenClass > 0,
                                          correctiveMaskSevenClass,
                                          globalSCArrayCorrected)

        del correctiveMaskSevenClass
        # END EDGE FIXING

        # SIBERIA WATER FLIPPING
        siberianInlandBox = correctiveMaskArray >> 7

        if self._debug:
            self._logger.debug('Siberian mask attrs')
            self._logger.debug(f'\tMax: {siberianInlandBox.max()}')
            self._logger.debug(f'\tMin: {siberianInlandBox.min()}')
            assert siberianInlandBox.max() == 1

        waterFlipConditional = (
            globalSevenClassNoShorelineArray == 0) & (siberianInlandBox == 1)

        if self._debug:
            waterFlips = np.count_nonzero(waterFlipConditional)
            self._logger.debug(f'Water flips: {waterFlips}')

        globalSCArrayCorrected = np.where(
            waterFlipConditional, 3, globalSCArrayCorrected
        )

        del siberianInlandBox
        # END SIBERIA WATER FLIPPING

        # START ITERATIVE INLAND OCEAN-ADJ FLIPPING
        for iter in range(0, self.NUM_INLAND_OC_ADJ_ITERS):
            self._logger.debug(f'Inland Ocean-Adj iter: {iter}')

            globalSCArrayCorrected = self.replaceAdjacentThrees(
                globalSCArrayCorrected)
        # END ITERATIVE INLAND OCEAN-ADJ FLIPPING

        return globalSCArrayCorrected

    # -------------------------------------------------------------------------
    # _generateGlobalWithShoreline
    # -------------------------------------------------------------------------
    def _generateGlobalWithShoreline(self,
                                     globalNoShoreCorrectedArray: np.ndarray,
                                     globalNoShorePath: pathlib.Path) -> None:
        """
        Given a corrected global SC product with no shoreline, breaks up the
        array and performs the shoreline algorithms and adds the result to the
        global SC product. Writes it out.
        """

        globalShorelinePath = self._outDir / \
            globalNoShorePath.name.replace('NoShoreline', 'Shoreline')

        if globalShorelinePath.exists():

            infoMsg = f'{globalShorelinePath} already exists. ' + \
                'Skipping generation process.'

            self._logger.info(infoMsg)

            return

        globalSevenClassNoShoreline = gdal.Open(str(globalNoShorePath),
                                                gdal.GA_ReadOnly)

        globalSevenClassNoShorelineAttributes = self._getRasterAndAttributes(
            globalSevenClassNoShoreline)

        if self._debug:
            self._logger.debug(globalSevenClassNoShorelineAttributes)

        # Apply shoreline alg to the corrected array
        sevenClassWithShorelineArray = self._generateShorelineParallel(
            globalNoShoreCorrectedArray)

        # Write out the results using the no-shore global product attrs
        self._writeGlobalShoreline(globalShorelinePath,
                                   sevenClassWithShorelineArray,
                                   globalSevenClassNoShorelineAttributes)

    # -------------------------------------------------------------------------
    # generateShorelineParallel
    # -------------------------------------------------------------------------
    def _generateShorelineParallel(self, sevenClass: np.ndarray) -> np.ndarray:
        """
        Breaks up the sevenClass global array and performs the seven-class
        shoreline generation algorithms on overlapping chunks in parallel.
        """

        self._logger.info('Applying parallel seven class shoreline generation')

        sevenClassWithShoreline = apply_parallel(
            self.generateSevenClassShoreline,
            sevenClass,
            chunks=self.PARALLEL_GRID_SIZE,
            depth=self.PARALLEL_OVERLAP,
            mode=self.PARALLEL_MODE,
            dtype=self.SC_DTYPE,
        )

        return sevenClassWithShoreline

    # -------------------------------------------------------------------------
    # generateSevenClassShoreline
    # -------------------------------------------------------------------------
    @staticmethod
    def generateSevenClassShoreline(sevenClass: np.ndarray) -> np.ndarray:
        """
        Generates and adds the shoreline to the global seven-class product.

        Args:
            sevenClass (np.ndarray): seven-class array without shoreline

        Returns:
            np.ndarray: seven-class array with shoreline added
        """
        inland = GlobalSevenClassMap.extractValueFromSevenClass(3,
                                                                sevenClass)

        shallow = GlobalSevenClassMap.extractValueFromSevenClass(0,
                                                                 sevenClass)
        moderate = GlobalSevenClassMap.extractValueFromSevenClass(6,
                                                                  sevenClass)
        deep = GlobalSevenClassMap.extractValueFromSevenClass(7,
                                                              sevenClass)

        # ---
        # Combine shallow, moderate, and deep classes into a single
        # binary array
        # ---
        ocean = shallow | moderate | deep

        shorelineInland = GlobalSevenClassMap.shoreline(inland)

        shorelineOcean = GlobalSevenClassMap.shoreline(ocean)

        shoreLine = GlobalSevenClassMap.postProcessShoreline(
            shorelineInland,
            shorelineOcean,
            sevenClass)

        scWithShoreLine = GlobalSevenClassMap.addShorelineToSevenClass(
            sevenClass,
            shoreLine,
            GlobalSevenClassMap.SHORELINE_VAL)

        return scWithShoreLine

    # -------------------------------------------------------------------------
    # extractValueFromSevenClass
    # -------------------------------------------------------------------------
    @staticmethod
    @njit()
    def extractValueFromSevenClass(valueToExtract: int,
                                   sevenClass: np.ndarray) -> np.ndarray:
        """Given a value, return a binary array where the returned value is 1
        if the sevenClass array value is equal to the value to extract.

        Args:
            valueToExtract (int): Value to find [1, 7]
            sevenClass (np.ndarray): Seven-class product array

        Returns:
            np.ndarray: binary numpy array
        """

        boolArrayMatchingCase = (sevenClass == valueToExtract)

        binaryArrayMatchingCase = np.where(boolArrayMatchingCase, 1, 0)

        return binaryArrayMatchingCase

    # -------------------------------------------------------------------------
    # shoreline
    # -------------------------------------------------------------------------
    @staticmethod
    def shoreline(arr_in: np.ndarray) -> np.ndarray:
        """
        Given an array, finds the boundaries and returns an array where 1
        represent the class boundaries.

        Args:
            arr_in (np.ndarray): numpy array input

        Returns:
            np.ndarray: output numpy array
        """

        arr = np.where(arr_in > 100, 1, arr_in)

        arr = np.where(arr != 1, 0, arr)

        bnd = find_boundaries(arr,
                              connectivity=2,
                              mode='outer',
                              background=0).astype(np.uint8)

        return bnd

    # -------------------------------------------------------------------------
    # postProcessShoreline
    # -------------------------------------------------------------------------
    @staticmethod
    @njit()
    def postProcessShoreline(shorelineInland: np.ndarray,
                             shorelineShallow: np.ndarray,
                             sevenClass: np.ndarray) -> np.ndarray:
        """Given the shoreline of the shallow water and the inland water
        (i.e. the only classes we would expect to have a shoreline), this
        function returns a single array that is the two shoreliens or'd
        together.

        Args:
            shorelineInland (np.ndarray):
                binary array of inland shoreline
            shorelineShallow (np.ndarray):
                binary array of shallow ocean shoreline
            sevenClass (np.ndarray):
                seven-class array

        Returns:
            np.ndarray: binary shoreline array
        """

        shoreLine = np.logical_or(shorelineInland, shorelineShallow)

        shoreLine = np.where(shoreLine, 1, 0)

        shoreLine = np.where((shoreLine == 1) & (sevenClass == 1), 1, 0)

        return shoreLine

    # -------------------------------------------------------------------------
    # addShorelineToSevenClass
    # -------------------------------------------------------------------------
    @staticmethod
    @njit()
    def addShorelineToSevenClass(sevenClass: np.ndarray,
                                 shoreLine: np.ndarray,
                                 shoreLineValue: int) -> np.ndarray:
        """Given a shoreline array and the seven class array, returns the seven
        class array with shoreline added.

        Args:
            sevenClass (np.ndarray): seven-class array
            shoreLine (np.ndarray): shoreline array
            shoreLineValue (int): seven-class shoreline value

        Returns:
            np.ndarray: seven-class array with shoreline added
        """

        sevenClassWithShoreline = np.where(shoreLine == 1,
                                           shoreLineValue,
                                           sevenClass)

        return sevenClassWithShoreline

    # -------------------------------------------------------------------------
    # writeGlobalShoreline
    # -------------------------------------------------------------------------
    def _writeGlobalShoreline(self,
                              globalShorelinePath: pathlib.Path,
                              sevenClassWithShoreline: np.ndarray,
                              globalSevenClassAttributesDict: dict) -> None:
        """
        Writes out the global seven-class product with shorelines to disk.

        Args:
            globalShorelinePath (pathlib.Path): output path
            sevenClassWithShoreline (np.ndarray):
                seven-class with shoreline array
            globalSevenClassAttributesDict (dict):
                Global seven class attributes dict. Uses attributes from
                global seven-class product without shoreline to write to disk.

        """

        driver = gdal.GetDriverByName('GTiff')

        rows, cols = sevenClassWithShoreline.shape

        transform = globalSevenClassAttributesDict['transform']

        projection = globalSevenClassAttributesDict['projection']

        datasetMeta = globalSevenClassAttributesDict['ds_metadata']

        datasetMeta['_FillValue'] = self.SC_NODATA

        bandMeta = globalSevenClassAttributesDict['band_metadata']

        bandDescription = globalSevenClassAttributesDict['band_description']

        ds = driver.Create(str(globalShorelinePath), cols, rows,
                           1, gdal.GDT_Byte, options=['COMPRESS=LZW'])

        ds.SetMetadata(datasetMeta)

        ds.SetGeoTransform(transform)

        ds.SetProjection(projection)

        band = ds.GetRasterBand(1)

        band.WriteArray(sevenClassWithShoreline, 0, 0)

        band.FlushCache()

        band.SetNoDataValue(self.SC_NODATA)

        band.SetMetadata(bandMeta)

        band.SetDescription(bandDescription)

    # -------------------------------------------------------------------------
    # validateFileExists
    # -------------------------------------------------------------------------
    @staticmethod
    def validateFileExists(filepath: pathlib.Path) -> None:
        """
        Checks if file exists, if not raises the appropriate message
        """

        if not filepath.exists():
            raise FileNotFoundError(str(filepath))

    # -------------------------------------------------------------------------
    # replaceAdjacentThrees
    # -------------------------------------------------------------------------
    @staticmethod
    def replaceAdjacentThrees(arr):
        # Define a mask for values 0, 6, and 7
        ocean_mask = np.isin(arr, GlobalSevenClassMap.OCEAN_SET)

        # Create a mask for elements equal to 3
        threes_mask = (arr == 3)

        # Create a mask for elements adjacent to 3s
        adjacent_mask = np.zeros_like(arr, dtype=bool)
        adjacent_mask[:-1, :] |= ocean_mask[1:, :]  # Check element below
        adjacent_mask[1:, :] |= ocean_mask[:-1, :]  # Check element above
        adjacent_mask[:, :-1] |= ocean_mask[:, 1:]  # Check element right
        adjacent_mask[:, 1:] |= ocean_mask[:, :-1]  # Check element left

        # Apply the mask for values 0, 6, and 7 and adjacent 3s
        replace_mask = threes_mask & adjacent_mask

        # Replace values with 10 where the mask is True
        arr[replace_mask] = GlobalSevenClassMap.REPLACEMENT_VALUE

        return arr


if __name__ == '__main__':
    hdfInputDir = 'MODTEST'
    outputDir = 'no_shore_testing_fix'

    globalSC = GlobalSevenClassMap(hdfDirectory=hdfInputDir,
                                   outputDir=outputDir)

    globalSC.generateGlobalSevenClass()
