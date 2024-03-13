from collections import namedtuple
import datetime
import os
import glob

from osgeo import gdal


DayRange = namedtuple('DayRange', 'start end')


# -----------------------------------------------------------------------------
# Class Utils
# -----------------------------------------------------------------------------
class Utils(object):

    INCLUSIONS = {'v00': DayRange(177, 256),  # 177 plus 5 16-day periods
                  'v01': DayRange(161, 256),  # 161 plus 7 16-day periods
                  'v02': DayRange(145, 288),  # 145 plus 9 16-day periods
                  'v03': DayRange(129, 304)}  # 129 plus 11 16-day periods

    EXCLUSIONS = {'v17': DayRange(72, 357),   # 357 plus 5 16-day periods
                  'v16': DayRange(88, 341),   # 341 plus 7 16-day periods
                  'v15': DayRange(104, 325),  # 325 plus 9 16-day periods
                  'v14': DayRange(120, 309)}  # 309 plus 11 16-day periods

    QA_ANTARCTIC_EXCLUSION = ['v17', 'v16', 'v15']

    # -------------------------------------------------------------------------
    # getImageName
    # -------------------------------------------------------------------------
    @staticmethod
    def getImageName(year, tile, sensor, classifier, day=None, postFix=None):

        name = str(year) + '-'

        if day:
            name += str(day).zfill(3) + '-'

        name += str(tile) + '-' + \
            str(sensor) + '-' + \
            str(classifier)

        if postFix:
            name += '-' + str(postFix)

        return name

    # -------------------------------------------------------------------------
    # writeRaster
    # -------------------------------------------------------------------------
    @staticmethod
    def writeRaster(outDir, pixels, name, cols=0, rows=0, projection=None,
                    transform=None):

        cols = pixels.shape[0]
        rows = pixels.shape[1] if len(pixels.shape) > 1 else 1
        imageName = os.path.join(outDir, name + '.tif')
        driver = gdal.GetDriverByName('GTiff')

        ds = driver.Create(imageName, cols, rows, 1, gdal.GDT_Int16,
                           options=['COMPRESS=LZW'])
        if projection:
            ds.SetProjection(projection)
        if transform:
            ds.SetGeoTransform(transform)

        ds.WriteRaster(0, 0, cols, rows, pixels.tobytes())

    # -------------------------------------------------------------------------
    # _getPostStr()
    # -------------------------------------------------------------------------
    @staticmethod
    def getPostStr():
        sdtdate = datetime.datetime.now()
        year = sdtdate.year
        hms = sdtdate.strftime('%H%M%S')
        sdtdate = sdtdate.timetuple()
        jdate = sdtdate.tm_yday
        post_str = '{}{:03}{}'.format(year, jdate, hms)
        return post_str

    # -------------------------------------------------------------------------
    # getStaticDatasetPath
    # -------------------------------------------------------------------------
    @staticmethod
    def getStaticDatasetPath(inDir, searchTerm) -> str:
        searchPath = os.path.join(
            inDir, searchTerm)
        staticPath = glob.glob(searchPath)
        if len(staticPath) > 0:
            staticPath = staticPath[0]
            return staticPath
        else:
            msg = '{} not found.'.format(searchPath)
            raise FileNotFoundError(msg)
