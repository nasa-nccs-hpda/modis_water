import datetime
import os

from osgeo import gdal


# -----------------------------------------------------------------------------
# Class Utils
# -----------------------------------------------------------------------------
class Utils(object):

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
    def writeRaster(outDir, pixels, name, cols=0, rows=0):

        cols = pixels.shape[0]
        rows = pixels.shape[1] if len(pixels.shape) > 1 else 1
        imageName = os.path.join(outDir, name + '.tif')
        driver = gdal.GetDriverByName('GTiff')

        ds = driver.Create(imageName, cols, rows, 1, gdal.GDT_Int16,
                           options=['COMPRESS=LZW'])

        ds.WriteRaster(0, 0, cols, rows, pixels.tobytes())

    # -------------------------------------------------------------------------
    # _getPostStr()
    # -------------------------------------------------------------------------
    @staticmethod
    def getPostStr():
        sdtdate = datetime.datetime.now()
        year = sdtdate.year
        hm = sdtdate.strftime('%H%M')
        sdtdate = sdtdate.timetuple()
        jdate = sdtdate.tm_yday
        post_str = '{}{:03}{}'.format(year, jdate, hm)
        return post_str
