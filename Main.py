""" the osgeo package contains the GDAL, OGR and OSR libraries """

""" for python 2 and python 3 execution exec(open("./path/to/script.py").read(), globals()) """

import sys, os, json

from osgeo import gdal, osr, ogr

sys.path.append('/usr/bin/')
import gdal_merge
import gdal_pansharpen

import generic

def Usage():
    print('Usage: trueColour(args)')

def trueColour(argv):

    inputdirectory = sys.argv[1]
    outputdirectory = sys.argv[2]
    platformname = sys.argv[3]
    producttype = sys.argv[4]
    if len(sys.argv) == 6:
        aoiwkt = sys.argv[5]
    else:   
        aoiwkt = None

    print gdal.VersionInfo()

    if platformname == 'SENTINEL2':
        # find SAFE directory
        for file in os.listdir(inputdirectory):
            filePath = inputdirectory + file
            print filePath
            if os.path.isdir(filePath) and filePath.endswith(".SAFE"):
                safeDirectory = filePath
                break
        if safeDirectory is None:
            sys.exit("Could not find SAFE directory")
        # retrieve the tiff file now
        descriptorPath = safeDirectory + "/MTD_MSIL1C.xml"
        print "Opening dataset " + descriptorPath
        ds = gdal.Open(descriptorPath)

        subdatasets = ds.GetMetadata_List("SUBDATASETS")
        for subdataset in subdatasets:
            if ":TCI:" in subdataset:
                tciFileName = subdataset.split("=")[1]
                break
        if tciFileName is None:
            sys.exit("Could not find true colour image in subdatasets")

        print "TCI file name " + tciFileName

        tciDs = gdal.Open(tciFileName)

        fileList = tciDs.GetFileList()

        for fileName in fileList:
            if fileName.endswith("_TCI.jp2"):
                jp2FilePath = fileName

        if jp2FilePath is None:
            sys.exit("Could not find jp2 file for true colour image")

        ds = gdal.Open(jp2FilePath)

        warpFilePath = outputdirectory + "/warped.vrt"
        productFootprintWKT = generateWarpFile(outputdirectory, warpFilePath, aoiwkt, ds)

        ds = gdal.Translate("temp", warpFilePath, outputType = gdal.GDT_Byte, options = ['PHOTOMETRIC=RGB'], format = 'MEM')
        executeOverviews(ds)
        outputFilePath = outputdirectory + '/productOutput.tiff'
        # TODO - check if 16 bits and if 16 bits reduce to 8 bits
        ds = gdal.Translate(outputFilePath, ds, format = 'GTiff')

        # now write the output json file
        product = {
            "name": "True colour image",
            "productType": "COVERAGE",
            "SRS":"EPSG:4326",
            "envelopCoordinatesWKT": productFootprintWKT,
            "filePath": outputFilePath,
            "description": "True colour image from Sentinel2 platform"
        }
        writeOutput(outputdirectory, "True colour generation using geocento process", [product])

        print "True Colour script finished for SENTINEL2 product(s) at " + inputdirectory

    elif platformname == 'LANDSAT8':
        bandFiles = []
        # get the required bands
        for file in os.listdir(inputdirectory):
            filePath = inputdirectory + file
            print filePath
            if filePath.upper().endswith("_B2.TIF") or \
                    filePath.upper().endswith("_B3.TIF") or \
                    filePath.upper().endswith("_B4.TIF"):
                bandFiles.append(filePath)
            elif filePath.upper().endswith("_B8.TIF"):
                band8FilePath = filePath

        if len(bandFiles) != 3 or band8FilePath is None:
            sys.exit("Missing bands in Landsat8 directory")

        # make sure the bands are arranged in the right order
        bandFiles = sorted(bandFiles, reverse = True)

        # create vrt for bands
        bandsFilePath = outputdirectory + '/spectral.vrt'
        gdal.BuildVRT(bandsFilePath, bandFiles, separate = True)

        panSharpenFilePath = outputdirectory + '/pansharpen.vrt';

        gdal_pansharpen.gdal_pansharpen(['', band8FilePath, bandsFilePath, panSharpenFilePath, '-nodata', '0', '-co', 'PHOTOMETRIC=RGB', '-of', 'VRT'])

        # stretch the values
        ds = gdal.Open(panSharpenFilePath)

        warpedFilePath = outputdirectory + '/warped.vrt'
        productFootprintWKT = generateWarpFile(outputdirectory, warpedFilePath, aoiwkt, ds)

        scaleParams = generic.getScaleParams(ds, 255)
        print scaleParams
        
        print 'Translating to tiff file'
        
        ps = gdal.Translate("temp", warpedFilePath, scaleParams = scaleParams, exponents = [0.5, 0.5, 0.5], outputType = gdal.GDT_Byte, options = ['PHOTOMETRIC=RGB'], format = 'MEM')
        
        print 'Generate overviews'
        executeOverviews(ps)
        
        print 'Save with overviews'
        outputFilePath = outputdirectory + '/productOutput.tiff'
        gdal.Translate(outputFilePath, ps, format = 'GTiff')

        # now write the output json file
        product = {
            "name": "True colour image",
            "productType": "COVERAGE",
            "SRS":"EPSG:4326",
            "envelopCoordinatesWKT": productFootprintWKT,
            "filePath": outputFilePath,
            "description": "True colour image from Landsat 8 platform"
        }
        writeOutput(outputdirectory, "True colour generation using geocento process", [product])

        print "True Colour script finished for LANDSAT8 STANDARD product(s) at " + inputdirectory

    elif platformname == 'LANDSAT7':
        bandFiles = []
        # get the required bands
        for file in os.listdir(inputdirectory):
            filePath = inputdirectory + file
            print filePath
            if filePath.upper().endswith("_B1.TIF") or \
                    filePath.upper().endswith("_B2.TIF") or \
                    filePath.upper().endswith("_B3.TIF"):
                bandFiles.append(filePath)
            elif filePath.upper().endswith("_B8.TIF"):
                band8FilePath = filePath

        if len(bandFiles) != 3 or band8FilePath is None:
            sys.exit("Missing bands in Landsat8 directory")

        # make sure the bands are arranged in the right order
        bandFiles = sorted(bandFiles, reverse = True)

        # create vrt for bands
        bandsFilePath = outputdirectory + '/spectral.vrt'
        gdal.BuildVRT(bandsFilePath, bandFiles, separate = True)

        panSharpenFilePath = outputdirectory + '/pansharpen.vrt';

        gdal_pansharpen.gdal_pansharpen(['', band8FilePath, bandsFilePath, panSharpenFilePath, '-nodata', '0', '-co', 'PHOTOMETRIC=RGB', '-of', 'VRT'])

        # stretch the values
        ds = gdal.Open(panSharpenFilePath)

        warpedFilePath = outputdirectory + '/warped.vrt'
        productFootprintWKT = generateWarpFile(outputdirectory, warpedFilePath, aoiwkt, ds)

        scaleParams = generic.getScaleParams(ds, 255)
        print scaleParams
        
        print 'Translating to tiff file'
        
        ps = gdal.Translate("temp", warpedFilePath, scaleParams = scaleParams, exponents = [0.5, 0.5, 0.5], outputType = gdal.GDT_Byte, options = ['PHOTOMETRIC=RGB'], format = 'MEM')
        
        print 'Generate overviews'
        executeOverviews(ps)
        
        print 'Save with overviews'
        outputFilePath = outputdirectory + '/productOutput.tiff'
        gdal.Translate(outputFilePath, ps, format = 'GTiff')

        # now write the output json file
        product = {
            "name": "True colour image",
            "productType": "COVERAGE",
            "SRS":"EPSG:4326",
            "envelopCoordinatesWKT": productFootprintWKT,
            "filePath": outputFilePath,
            "description": "True colour image from Landsat 7 platform"
        }
        writeOutput(outputdirectory, "True colour generation using geocento process", [product])

        print "True Colour script finished for LANDSAT7 STANDARD product(s) at " + inputdirectory

    elif platformname == 'TRIPPLESAT' or platformname == 'DEIMOS-2':
        # get the tif files
        tifFiles = findFiles(inputdirectory, 'tif')

        if len(tifFiles) == 0:
            sys.exit("Missing TIFF file in directory")

        tifFile = tifFiles[0]

        # create overlays and extract footprint
        ds = gdal.Open(tifFile)
        # reproject to 4326
        tempFilePath = outputdirectory + '/temp.tiff';
        ds = gdal.Warp(tempFilePath, ds, format = 'GTiff', dstSRS = 'EPSG:4326')
        productFootprintWKT = generic.getDatasetFootprint(ds)
        print "FOOTPRINT: " + productFootprintWKT
        executeOverviews(ds)
        outputFilePath = outputdirectory + '/productOutput.tiff'
        ds = gdal.Translate(outputFilePath, ds, bandList = [1,2,3], outputType = gdal.GDT_Byte, noData = 0, format = 'GTiff')

        # now write the output json file
        product = {
            "name": "True colour image",
            "productType": "COVERAGE",
            "SRS":"EPSG:4326",
            "envelopCoordinatesWKT": productFootprintWKT,
            "filePath": outputFilePath,
            "description": "True colour image from TrippleSat platform"
        }

        writeOutput(outputdirectory, "True colour generation using geocento process", [product])

        print "True Colour script finished for TRIPPLE SAT product(s) at " + inputdirectory

    elif platformname == 'PLEIADES':
        # TODO - check more formats
        # get the jp2 files
        jp2Files = findFiles(inputdirectory, 'jp2')
        isJpeg2000 = len(jp2Files) > 0

        if isJpeg2000:
            # simple case, we have a pan sharpened image
            if len(jp2Files) == 1:
                imageFile = jp2Files[0]
            else:
                # find out abut MS and PAN
                msDirectory = findDirectory(inputdirectory, "_MS_")
                panDirectory = findDirectory(inputdirectory, "_P_")
                msFiles = findFiles(msDirectory[0], 'jp2')
                panFiles = findFiles(panDirectory[0], 'jp2')
                imageFile = panSharpen(outputdirectory, panFiles, msFiles)
        else:
            # try with tif instead
            tifFiles = findFiles(inputdirectory, ('tiff', 'tif'))
            # simple case, we have a pan sharpened image
            if len(tifFiles) == 1:
                imageFile = tifFiles[0]
            elif len(tifFiles) > 1:
                msDirectory = findDirectory(inputdirectory, "_MS_")
                panDirectory = findDirectory(inputdirectory, "_P_")
                msFiles = findFiles(msDirectory[0], ('tiff', 'tif'))
                panFiles = findFiles(panDirectory[0], ('tiff', 'tif'))
                imageFile = panSharpen(outputdirectory, panFiles, msFiles)
            else:
                sys.exit("Missing image file in directory")

        # create overlays and extract footprint
        ds = gdal.Open(imageFile)
        # reproject to 4326
        tempFilePath = outputdirectory + '/temp.tiff';
        ds = gdal.Warp(tempFilePath, ds, format = 'GTiff', dstSRS = 'EPSG:4326')
        productFootprintWKT = generic.getDatasetFootprint(ds)
        print "FOOTPRINT: " + productFootprintWKT

        # stretch to bytes
        scaleParams = generic.getScaleParams(ds, 255)
        print "Scale params "
        print(scaleParams)
        outputFilePath = outputdirectory + '/productOutput.tiff'
        ds = gdal.Translate(outputFilePath, ds, bandList = [1,2,3], scaleParams = scaleParams, exponents = [0.5, 0.5, 0.5], outputType = gdal.GDT_Byte, noData = 0, format = 'GTiff')
        executeOverviews(ds)

        # now write the output json file
        product = {
            "name": "True colour image",
            "productType": "COVERAGE",
            "SRS":"EPSG:4326",
            "envelopCoordinatesWKT": productFootprintWKT,
            "filePath": outputFilePath,
            "description": "True colour image from Pleiades platform"
        }

        writeOutput(outputdirectory, "True colour generation using geocento process", [product])

        print "True Colour script finished for PLEIADES product(s) at " + inputdirectory

    elif platformname == 'WORLDVIEW-2':
        # get the tif files
        tiffFiles = findFiles(inputdirectory, 'tif')

        if len(tiffFiles) == 0:
            sys.exit("Missing TIFF file in directory")

        #/ check if bundle type of product
        if len(tiffFiles) == 2:
            if "_PAN/" in tiffFiles[0]:
                panFile = tiffFiles[0]
                bandFile = tiffFiles[1]
            else:
                panFile = tiffFiles[1]
                bandFile = tiffFiles[0]
            # pan sharpen the image
            panSharpenFilePath = outputdirectory + '/pansharpen.tiff';
            sys.argv = ['/usr/bin/gdal_pansharpen.py', '-nodata', '0', panFile, bandFile, panSharpenFilePath]
            print sys.argv
            gdal_pansharpen.main()
            tiffFile = panSharpenFilePath
        else:
            tiffFile = tiffFiles[0]

        # create overlays and extract footprint
        ds = gdal.Open(tiffFile)
        # reproject to 4326
        tempFilePath = outputdirectory + '/temp.tiff';
        ds = gdal.Warp(tempFilePath, ds, format = 'GTiff', dstSRS = 'EPSG:4326')
        productFootprintWKT = generic.getDatasetFootprint(ds)
        print "FOOTPRINT: " + productFootprintWKT
        
        # stretch to bytes
        scaleParams = generic.getScaleParams(ds, 255)
        print "Scale params "
        print(scaleParams)
        outputFilePath = outputdirectory + '/productOutput.tiff'
        ds = gdal.Translate(outputFilePath, ds, bandList = [1,2,3], scaleParams = scaleParams, outputType = gdal.GDT_Byte, noData = 0, format = 'GTiff')
        executeOverviews(ds)

        # now write the output json file
        product = {
            "name": "True colour image",
            "productType": "COVERAGE",
            "SRS":"EPSG:4326",
            "envelopCoordinatesWKT": productFootprintWKT,
            "filePath": outputFilePath,
            "description": "True colour image from Worldview-2 platform"
        }

        writeOutput(outputdirectory, "True colour generation using geocento process", [product])

        print "Now cleaning up"
        os.remove(tempFilePath)

        print "True Colour script finished for WorldView-2 product(s) at " + inputdirectory

    elif platformname == 'SUPERVIEW':
        # get the tif files
        tiffFiles = findFiles(inputdirectory, ('tiff', 'tif'))

        if len(tiffFiles) == 0:
            sys.exit("Missing TIFF file in directory")

        # check if pan sharpened version exists
        if len(tiffFiles) == 1:
            tiffFile = tiffFiles[0]
        elif len(tiffFiles) == 3:
            # look for the pan sharpened version
            for fileName in tiffFiles:
                if 'PSH.tif' in fileName:
                    tiffFile = fileName
                    print "Found pan sharpened tiff file at " + tiffFile;
                    break;
        # check if bundle type of product
        elif len(tiffFiles) == 2:
            if "-PAN.tiff" in tiffFiles[0]:
                panFile = tiffFiles[0]
                bandFile = tiffFiles[1]
            else:
                panFile = tiffFiles[1]
                bandFile = tiffFiles[0]
            # pan sharpen the image
            panSharpenFilePath = outputdirectory + '/pansharpen.tiff';
            if os.path.isfile(panSharpenFilePath):
                tiffFile = panSharpenFilePath
                print "Pan sharpened file already exists"
            else:
                # if no projection is available
                # reproject first
                ds = gdal.Open(bandFile)
                gdal.Warp(bandFile, ds, format = 'GTiff', dstSRS = 'EPSG:4326')
                ds = gdal.Open(panFile)
                gdal.Warp(panFile, ds, format = 'GTiff', dstSRS = 'EPSG:4326')
                # now pansharpen the image
                sys.argv = ['/usr/bin/gdal_pansharpen.py', '-nodata', '0', panFile, bandFile, panSharpenFilePath]
                print sys.argv
                gdal_pansharpen.main()
                tiffFile = panSharpenFilePath

        ds = gdal.Open(tiffFile)
        # create overlays and extract footprint
        # reproject to 4326
        tempFilePath = outputdirectory + '/temp.tiff';
        ds = gdal.Warp(tempFilePath, ds, format = 'GTiff', dstSRS = 'EPSG:4326')
        productFootprintWKT = generic.getDatasetFootprint(ds)
        print "FOOTPRINT: " + productFootprintWKT
        
        # stretch to bytes
        scaleParams = generic.getScaleParams(ds, 255)
        print "Scale params "
        print(scaleParams)
        outputFilePath = outputdirectory + '/productOutput.tiff'
        ds = gdal.Translate(outputFilePath, ds, bandList = [3,2,1], scaleParams = [scaleParams[2], scaleParams[1], scaleParams[0]], outputType = gdal.GDT_Byte, noData = 0, format = 'GTiff')
        executeOverviews(ds)

        # now write the output json file
        product = {
            "name": "True colour image",
            "productType": "COVERAGE",
            "SRS":"EPSG:4326",
            "envelopCoordinatesWKT": productFootprintWKT,
            "filePath": outputFilePath,
            "description": "True colour image from SuperView platform"
        }

        writeOutput(outputdirectory, "True colour generation using geocento process", [product])

        print "Now cleaning up"
        os.remove(tempFilePath)

        print "True Colour script finished for SuperView product(s) at " + inputdirectory

    elif platformname == 'KOMPSAT-2':
        # get the tif files
        tiffFiles = findFiles(inputdirectory, 'tif')

        if len(tiffFiles) == 0:
            sys.exit("Missing TIFF file in directory")

        #/ check if bundle type of product
        if len(tiffFiles) == 2:
            if "_PAN/" in tiffFiles[0]:
                panFile = tiffFiles[0]
                bandFile = tiffFiles[1]
            else:
                panFile = tiffFiles[1]
                bandFile = tiffFiles[0]
            # pan sharpen the image
            panSharpenFilePath = outputdirectory + '/pansharpen.tiff';
            sys.argv = ['/usr/bin/gdal_pansharpen.py', '-nodata', '0', panFile, bandFile, panSharpenFilePath]
            print sys.argv
            gdal_pansharpen.main()
            tiffFile = panSharpenFilePath
        else:
            tiffFile = tiffFiles[0]

        [productFootprintWKT, outputFilePath] = warpTranslateOverview(tiffFile, outputdirectory, aoiwkt)
        if False:
            # create overlays and extract footprint
            ds = gdal.Open(tiffFile)
            # reproject to 4326
            tempFilePath = outputdirectory + '/temp.tiff';
            ds = gdal.Warp(tempFilePath, ds, format = 'GTiff', dstSRS = 'EPSG:4326')
            productFootprintWKT = generic.getDatasetFootprint(ds)
            print "FOOTPRINT: " + productFootprintWKT
            
            # stretch to bytes
            scaleParams = generic.getScaleParams(ds, 255)
            outputFilePath = outputdirectory + '/productOutput.tiff'
            ds = gdal.Translate(outputFilePath, ds, bandList = [1,2,3], scaleParams = scaleParams, exponents = [0.5, 0.5, 0.5], outputType = gdal.GDT_Byte, options = ['PHOTOMETRIC=RGB'], format = 'GTiff')
            executeOverviews(ds)

        # now write the output json file
        product = {
            "name": "True colour image",
            "productType": "COVERAGE",
            "SRS":"EPSG:4326",
            "envelopCoordinatesWKT": productFootprintWKT,
            "filePath": outputFilePath,
            "description": "True colour image from Kompsat-2 platform"
        }

        writeOutput(outputdirectory, "True colour generation using geocento process", [product])

        print "Now cleaning up"
        #os.remove(tempFilePath)

        print "True Colour script finished for kompsat-2 product(s) at " + inputdirectory

    elif platformname == 'KOMPSAT-3' or platformname == 'KOMPSAT-3A':
        # get the tif files
        tiffFiles = findFiles(inputdirectory, 'tif')

        if len(tiffFiles) == 0:
            sys.exit("Missing TIFF file in directory")

        #/ check if bundle type of product
        if len(tiffFiles) == 2:
            if "_PAN/" in tiffFiles[0]:
                panFile = tiffFiles[0]
                bandFile = tiffFiles[1]
            else:
                panFile = tiffFiles[1]
                bandFile = tiffFiles[0]
        elif len(tiffFiles) == 4:
            # pan sharpened bands
            bandFiles = sorted(tiffFiles, reverse = True)
            # remove the NIR band
            del(bandFiles[1])
            # merge all files into one
            # create vrt for bands
            bandsFilePath = outputdirectory + '/spectral.vrt'
            gdal.BuildVRT(bandsFilePath, bandFiles, separate = True)
            ds = gdal.Open(bandsFilePath)
        else:
            tiffFile = tiffFiles[0]

        warpedFilePath = outputdirectory + '/warped.vrt'
        #ds = gdal.Warp(warpedFilePath, bandsFilePath, format = 'VRT', dstSRS = 'EPSG:4326')
        productFootprintWKT = generateWarpFile(outputdirectory, warpedFilePath, aoiwkt, ds)
        #productFootprintWKT = aoiwkt

        scaleParams = generic.getScaleParams(ds, 255)
        print scaleParams
        
        print 'Translating to tiff file'
        
        tempFilePath = outputdirectory + '/temp.tiff'
        ps = gdal.Translate(tempFilePath, warpedFilePath, scaleParams = scaleParams, outputType = gdal.GDT_Byte, options = ['PHOTOMETRIC=RGB'], format = 'GTiff')
        
        print 'Generate overviews'
        executeOverviews(ps)
        
        print 'Save with overviews'
        outputFilePath = outputdirectory + '/productOutput.tiff'
        gdal.Translate(outputFilePath, ps, format = 'GTiff')

        # now write the output json file
        product = {
            "name": "True colour image",
            "productType": "COVERAGE",
            "SRS":"EPSG:4326",
            "envelopCoordinatesWKT": productFootprintWKT,
            "filePath": outputFilePath,
            "description": "True colour image from Kompsat-3 platform"
        }

        writeOutput(outputdirectory, "True colour generation using geocento process", [product])

        print "True Colour script finished for kompsat-3 product(s) at " + inputdirectory

    elif platformname == 'PLANETSCOPE':
        # get the tif files
        tifFiles = findFiles(inputdirectory, 'tif')

        if len(tifFiles) == 0:
            sys.exit("Missing TIFF file in directory")

        for file in tifFiles:
            ds = gdal.Open(file)
            if ds.RasterCount > 1:
                tifFile = file
                break
        # check if visual or analytics
        analytic = "Analytic" in tifFile

        # create overlays and extract footprint
        ds = gdal.Open(tifFile)
        # reproject to 4326
        tempFilePath = outputdirectory + '/temp.tiff';
        outputFilePath = outputdirectory + '/productOutput.tiff'
        # reduce bands if needed
        ds = gdal.Translate('temp', ds, format = 'MEM', bandList = [3,2,1])
        # if analytics we need to do some scaling for contrasts
        if analytic:
            print "Analytic product, modifying contrast for visualisation"
            scaleParams = generic.getScaleParams(ds, 255)
            print "Scale params "
            print(scaleParams)
            ds = gdal.Translate('temp', ds, format = 'MEM', scaleParams = scaleParams, exponents = [0.5, 0.5, 0.5])
        ds = gdal.Warp('temp', ds, format = 'GTiff', srcNodata = 0, dstAlpha = True, dstSRS = 'EPSG:4326')
        productFootprintWKT = generic.getDatasetFootprint(ds)
        print "FOOTPRINT: " + productFootprintWKT
        ds = gdal.Translate(tempFilePath, ds, outputType = gdal.GDT_Byte, format = 'GTiff')
        executeOverviews(ds)
        ds = gdal.Translate(outputFilePath, ds, format = 'GTiff')

        # now write the output json file
        product = {
            "name": "True colour image",
            "productType": "COVERAGE",
            "SRS":"EPSG:4326",
            "envelopCoordinatesWKT": productFootprintWKT,
            "filePath": outputFilePath,
            "description": "True colour image from TrippleSat platform"
        }

        writeOutput(outputdirectory, "True colour generation using geocento process", [product])

        print "True Colour script finished for TRIPPLE SAT product(s) at " + inputdirectory

    elif platformname == 'SENTINEL1':
        pass
    else:
        sys.exit("Unknown platform " + platformname)
        
def generateWarpFile(outputdirectory, warpedFilePath, aoiwkt, ds):
    footprintGeometryWKT = generic.getDatasetFootprint(ds)
    if aoiwkt is not None:
        gdal.SetConfigOption('GDALWARP_DENSIFY_CUTLINE', 'NO')
        intersectionWKT = generic.calculateCutline(footprintGeometryWKT, aoiwkt)
        print "FOOTPRINT: " + footprintGeometryWKT
        print "AOI: " + aoiwkt
        print "INTERSECTION: " + intersectionWKT
        
        csvFileDirectory = outputdirectory
        csvFilePath = generic.createCutline(csvFileDirectory, intersectionWKT)
        
        gdal.Warp(warpedFilePath, ds, format = 'VRT', cutlineDSName = csvFilePath, srcNodata = 0, dstAlpha = True, cropToCutline = True, dstSRS = 'EPSG:4326', warpOptions = ['GDALWARP_DENSIFY_CUTLINE=NO'])
        
        return intersectionWKT
    else:
        gdal.Warp(warpedFilePath, ds, format = 'VRT', srcNodata = 0, dstAlpha = True, dstSRS = 'EPSG:4326')
        return footprintGeometryWKT

def findFiles(directory, extension):
    print "scanning directory " + directory + " for files with extension " + str(extension)
    foundFiles = []
    for dirpath, dirnames, files in os.walk(directory):
        for name in files:
            print "file " + name
            if name.lower().endswith(extension):
                print "Adding file " + name + " at " + dirpath
                foundFiles.append(os.path.join(dirpath, name))
    return foundFiles

def findDirectory(directory, substring):
    print "scanning directory " + directory + " for directories with pattern " + str(substring)
    foundFiles = []
    for dirpath, dirnames, files in os.walk(directory):
        for name in dirnames:
            print "directory " + name
            if substring.lower() in name.lower():
                print "Adding directory " + name + " at " + dirpath
                foundFiles.append(os.path.join(dirpath, name))
    return foundFiles

def warpTranslateOverview(panSharpenFilePath, outputdirectory, aoiwkt):
    ds = gdal.Open(panSharpenFilePath)

    warpedFilePath = outputdirectory + '/warped.vrt'
    productFootprintWKT = generateWarpFile(outputdirectory, warpedFilePath, aoiwkt, ds)

    scaleParams = generic.getScaleParams(ds, 255)
    print scaleParams
    
    print 'Translating to tiff file'
    
    # check size of image
    fileSize = ds.RasterXSize * ds.RasterYSize
    localOperation = fileSize > 10000 * 10000
    tempFile = outputdirectory + "/temp.tif"
    if localOperation:
        ps = gdal.Translate(tempFile, warpedFilePath, scaleParams = scaleParams, exponents = [0.5, 0.5, 0.5], outputType = gdal.GDT_Byte, options = ['PHOTOMETRIC=RGB'], format = 'GTIFF')
    else:
        ps = gdal.Translate("temp", warpedFilePath, scaleParams = scaleParams, exponents = [0.5, 0.5, 0.5], outputType = gdal.GDT_Byte, options = ['PHOTOMETRIC=RGB'], format = 'MEM')
    
    print 'Generate overviews'
    executeOverviews(ps)
    
    print 'Save with overviews'
    outputFilePath = outputdirectory + '/productOutput.tiff'
    gdal.Translate(outputFilePath, ps, format = 'GTiff')
    
    if localOperation:
        os.remove(tempFile)
    
    return [productFootprintWKT, outputFilePath]

def executeWarp(ds, cutlineFilePath):
    return gdal.Warp('temp', ds, format = 'MEM', cutlineDSName = cutlineFilePath, srcNodata = 0, dstAlpha = True, cropToCutline = True, dstSRS = 'EPSG:4326')

def calculateCutline(footprintGeometryWKT, aoiWKT):
    # calculate intersection
    if aoiWKT is None:
        print "No intersection provided!"
        return

    aoiGeometry = ogr.CreateGeometryFromWkt(aoiWKT)
    footprintGeometry = ogr.CreateGeometryFromWkt(footprintGeometryWKT)

    intersectionGeometry = footprintGeometry.Intersection(aoiGeometry)
    if intersectionGeometry is None:
        return

    return intersectionGeometry.ExportToWkt()


def createCutline(directory, footprintGeometryWKT, aoiWKT):
    createCutline(directory, calculateCutline(footprintGeometryWKT, aoiWKT))

def createCutline(directory, intersectionWKT):
    if intersectionWKT is None:
        return

    csvFileName = directory + '/cutline.csv'
    csvFile = open(csvFileName, 'w')
    csvFile.write('ID, WKT\n')
    csvFile.write('1, "' + intersectionWKT + '"\n')
    csvFile.close()
    prjFile = open(directory + '/cutline.prj', 'w')
    prjFile.write('EPSG:4326')
    prjFile.close()

    return csvFileName


def executeOverviews(ds):
    # TODO - calculate based on the size of the image
    overviewList = [2, 4, 8, 16, 32]
    ds.BuildOverviews( "NEAREST", overviewList)

def writeOutput(directory, message, products):
    outputValues = {
        "message": message,
        "products": products
    }
    with open(directory + '/output.json', 'w') as outfile:
        json.dump(outputValues, outfile)

def panSharpen(outputdirectory, panFiles, bandFiles):
    args = ['/usr/bin/gdal_pansharpen.py', '-nodata', '0']
    
    # create VRT with the files
    if len(panFiles) == 1:
        panFilePath = panFiles[0]
    elif len(panFiles) > 1:
        # mosaic the tif files
        panFilePath = outputdirectory + '/test.vrt'
        gdal.BuildVRT(panFilePath, panFiles)
    else:
        sys.exit('No pan files')
    
    args.append(panFilePath)
    
    if len(bandFiles) == 1:
        args.append(bandFiles[0])
    elif len(bandFiles) == 3:
        # assumes bands are in the right order
        args.append(bandFiles[0] + ",band=1")
        args.append(bandFiles[1] + ",band=2")
        args.append(bandFiles[2] + ",band=3")
    else:
        sys.exit('No pan files')
    
    # pan sharpen the image
    panSharpenFilePath = outputdirectory + '/pansharpen.tiff'
    args.append(panSharpenFilePath)
    sys.argv = args
    print(sys.argv)
    gdal_pansharpen.main()
    
    if not os.path.exists(panSharpenFilePath):
        sys.exit("Pansharpen failed, no file at " + panSharpenFilePath)
        
    return panSharpenFilePath

def main():
    return trueColour(sys.argv)

if __name__ == '__main__':
    sys.exit(trueColour(sys.argv))
