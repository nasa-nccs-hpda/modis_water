from osgeo import gdal
import numpy as np
from scipy.ndimage import binary_dilation

from modis_water.model.BandReader import BandReader
from modis_water.model.Utils import Utils


# -------------------------------------------------------------------------
# ImperviousMap
# -------------------------------------------------------------------------
class ImperviousMap(object):

    DTYPE: np.dtype = np.uint8
    COLS: int = 2400
    ROWS: int = 2400

    PERCENTAGE_CUTOFF_FLOOR: int = 75
    PERCENTAGE_CUTOFF_CEIL: int = 100
    PERCENTAGE_NODATA: int = 255
    BUFFER_PIXEL_AMOUNT: int = 1

    IMPERVIOUS_NAME_PRE_STR: str = 'Imp_Surf_'
    IMPERVIOUS_NAME_POST_STR: str = '_250m.tif'

    # -------------------------------------------------------------------------
    # generateImperviousBinaryMask
    # -------------------------------------------------------------------------
    @staticmethod
    def generateImperviousBinaryMask(
            tile: str, imperviousDir: str) -> np.ndarray:
        """
        Function to threshold the static impervious surface masks into
        binary masks. Anything between 75 and 100 percent is considered
        impervious while anything below 75 is considered permeable.
        Ref: MODIS_ewater_algorithm_MODIS_v2 1.d.v.2-3
        """
        imperviousDataArray = ImperviousMap._getImperviousPercentageArray(
            tile, imperviousDir)
        imperviousInRange = (
            (imperviousDataArray >= ImperviousMap.PERCENTAGE_CUTOFF_FLOOR) &
            (imperviousDataArray <= ImperviousMap.PERCENTAGE_CUTOFF_CEIL))
        imperviousThresholded = np.where(
            imperviousInRange, 1, 0).astype(ImperviousMap.DTYPE)
        imperviousOutputFlipped = imperviousThresholded ^ 1
        imperviousDialated = ImperviousMap._dialateImpervious(
            imperviousOutputFlipped)
        imperviousOutput = imperviousDialated ^ 1
        return imperviousOutput

    # -------------------------------------------------------------------------
    # _dialateImpervious
    # -------------------------------------------------------------------------
    @staticmethod
    def _dialateImpervious(imperviousArray: np.ndarray) -> np.ndarray:
        """
        Buffer out the 0s via the kernel below. According to MODIS Water
        Algorithm doc 1.d.v.3
        """
        kernel = np.array([[0, 1, 0],
                           [1, 0, 1],
                           [0, 1, 0]])
        dilatedArray = binary_dilation(imperviousArray, structure=kernel, )
        return dilatedArray

    # -------------------------------------------------------------------------
    # _getImperviousPercentageArray
    # -------------------------------------------------------------------------
    @staticmethod
    def _getImperviousPercentageArray(
            tile: str, imperviousDir: str) -> np.ndarray:
        """
        Search for the static impervious surface dataset. If not found, check
        to make sure we aren't in an antarctic tile (there are no impervious
        surface masks for those tiles).
        """
        exclusionTile = tile[3:] in Utils.QA_ANTARCTIC_EXCLUSION
        try:
            imperviousSearchTerm = ImperviousMap.IMPERVIOUS_NAME_PRE_STR + \
                tile + ImperviousMap.IMPERVIOUS_NAME_POST_STR
            imperviousDatasetPath = Utils.getStaticDatasetPath(
                imperviousDir, imperviousSearchTerm)
            imperviousDataset = gdal.Open(imperviousDatasetPath)
            imperviousDataArray = imperviousDataset.GetRasterBand(
                1).ReadAsArray()
        except FileNotFoundError as initialException:
            if exclusionTile:
                imperviousDataArray = np.zeros(
                    (BandReader.COLS, BandReader.ROWS),
                    dtype=ImperviousMap.DTYPE,)
            else:
                raise initialException
        return imperviousDataArray
