""" the osgeo package contains the GDAL, OGR and OSR libraries """

""" for python 2 and python 3 execution exec(open("./path/to/script.py").read(), globals()) """

import sys, os, json

from osgeo import gdal, osr, ogr

sys.path.append('/usr/bin/')
import gdal_merge
import gdal_pansharpen
import time

import generic

def Usage():
    print('Usage: trueColour(args)')

def trueColour(argv):

    inputDirectory = sys.argv[1]
    outputDirectory = sys.argv[2]
    platformName = sys.argv[3]
    producttype = sys.argv[4]
    if len(sys.argv) == 6:
        aoiwkt = sys.argv[5]
    else:   
        aoiwkt = None

    print "GDAL version " + gdal.VersionInfo()
    print "Platform name" + platformName
    print "Product type " + producttype
    print "AoI WKT " + aoiwkt

    if platformName == 'SENTINEL2':
        # find SAFE directory
        for file in os.listdir(inputDirectory):
            filePath = inputDirectory + file
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

        warpFilePath = outputDirectory + "/warped.vrt"
        productFootprintWKT = generateWarpFile(outputDirectory, warpFilePath, aoiwkt, ds)

        ds = gdal.Translate("temp", warpFilePath, outputType = gdal.GDT_Byte, options = ['PHOTOMETRIC=RGB'], format = 'MEM')
        executeOverviews(ds)
        outputFilePath = outputDirectory + '/productOutput.tiff'
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
        writeOutput(outputDirectory, "True colour generation using geocento process", [product])

        print "True Colour script finished for SENTINEL2 product(s) at " + inputDirectory

    elif platformName == 'LANDSAT8':
        bandFiles = []
        # get the required bands
        for file in os.listdir(inputDirectory):
            filePath = inputDirectory + file
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
        bandsFilePath = outputDirectory + '/spectral.vrt'
        gdal.BuildVRT(bandsFilePath, bandFiles, separate = True)

        panSharpenFilePath = outputDirectory + '/pansharpen.vrt';

        gdal_pansharpen.gdal_pansharpen(['', band8FilePath, bandsFilePath, panSharpenFilePath, '-nodata', '0', '-co', 'PHOTOMETRIC=RGB', '-of', 'VRT'])

        # stretch the values
        ds = gdal.Open(panSharpenFilePath)

        warpedFilePath = outputDirectory + '/warped.vrt'
        productFootprintWKT = generateWarpFile(outputDirectory, warpedFilePath, aoiwkt, ds)

        scaleParams = generic.getScaleParams(ds, 255)
        print scaleParams
        
        print 'Translating to tiff file'
        
        ps = gdal.Translate("temp", warpedFilePath, scaleParams = scaleParams, exponents = [0.5, 0.5, 0.5], outputType = gdal.GDT_Byte, options = ['PHOTOMETRIC=RGB'], format = 'MEM')
        
        print 'Generate overviews'
        executeOverviews(ps)
        
        print 'Save with overviews'
        outputFilePath = outputDirectory + '/productOutput.tiff'
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
        writeOutput(outputDirectory, "True colour generation using geocento process", [product])

        print "True Colour script finished for LANDSAT8 STANDARD product(s) at " + inputDirectory

    elif platformName == 'LANDSAT7':
        bandFiles = []
        # get the required bands
        for file in os.listdir(inputDirectory):
            filePath = inputDirectory + file
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
        bandsFilePath = outputDirectory + '/spectral.vrt'
        gdal.BuildVRT(bandsFilePath, bandFiles, separate = True)

        panSharpenFilePath = outputDirectory + '/pansharpen.vrt';

        gdal_pansharpen.gdal_pansharpen(['', band8FilePath, bandsFilePath, panSharpenFilePath, '-nodata', '0', '-co', 'PHOTOMETRIC=RGB', '-of', 'VRT'])

        # stretch the values
        ds = gdal.Open(panSharpenFilePath)

        warpedFilePath = outputDirectory + '/warped.vrt'
        productFootprintWKT = generateWarpFile(outputDirectory, warpedFilePath, aoiwkt, ds)

        scaleParams = generic.getScaleParams(ds, 255)
        print scaleParams
        
        print 'Translating to tiff file'
        
        ps = gdal.Translate("temp", warpedFilePath, scaleParams = scaleParams, exponents = [0.5, 0.5, 0.5], outputType = gdal.GDT_Byte, options = ['PHOTOMETRIC=RGB'], format = 'MEM')
        
        print 'Generate overviews'
        executeOverviews(ps)
        
        print 'Save with overviews'
        outputFilePath = outputDirectory + '/productOutput.tiff'
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
        writeOutput(outputDirectory, "True colour generation using geocento process", [product])

        print "True Colour script finished for LANDSAT7 STANDARD product(s) at " + inputDirectory

    elif platformName == 'TRIPPLESAT' or platformName == 'DEIMOS-2':
        # get the tif files
        tifFiles = findFiles(inputDirectory, 'tif')

        if len(tifFiles) == 0:
            sys.exit("Missing TIFF file in directory")

        tifFile = tifFiles[0]

        # create overlays and extract footprint
        ds = gdal.Open(tifFile)
        # reproject to 4326
        tempFilePath = outputDirectory + '/temp.tiff';
        ds = gdal.Warp(tempFilePath, ds, format = 'GTiff', dstSRS = 'EPSG:4326')
        productFootprintWKT = generic.getDatasetFootprint(ds)
        print "FOOTPRINT: " + productFootprintWKT
        executeOverviews(ds)
        outputFilePath = outputDirectory + '/productOutput.tiff'
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

        writeOutput(outputDirectory, "True colour generation using geocento process", [product])

        print "True Colour script finished for TRIPPLE SAT product(s) at " + inputDirectory

    elif platformName == 'PLEIADES':
        # TODO - check more formats
        # get the jp2 files
        jp2Files = findFiles(inputDirectory, 'jp2')
        isJpeg2000 = len(jp2Files) > 0

        if isJpeg2000:
            # simple case, we have a pan sharpened image
            if len(jp2Files) == 1:
                imageFile = jp2Files[0]
            else:
                # find out abut MS and PAN
                msDirectory = findDirectory(inputDirectory, "_MS_")
                panDirectory = findDirectory(inputDirectory, "_P_")
                msFiles = findFiles(msDirectory[0], 'jp2')
                panFiles = findFiles(panDirectory[0], 'jp2')
                imageFile = panSharpen(outputDirectory, panFiles, msFiles)
        else:
            # try with tif instead
            tifFiles = findFiles(inputDirectory, ('tiff', 'tif'))
            # simple case, we have a pan sharpened image
            if len(tifFiles) == 1:
                imageFile = tifFiles[0]
            elif len(tifFiles) > 1:
                msDirectory = findDirectory(inputDirectory, "_MS_")
                panDirectory = findDirectory(inputDirectory, "_P_")
                msFiles = findFiles(msDirectory[0], ('tiff', 'tif'))
                panFiles = findFiles(panDirectory[0], ('tiff', 'tif'))
                imageFile = panSharpen(outputDirectory, panFiles, msFiles)
            else:
                sys.exit("Missing image file in directory")

        # create overlays and extract footprint
        ds = gdal.Open(imageFile)
        warpedFilePath = outputDirectory + '/warped.vrt'
        productFootprintWKT = generateWarpFile(outputDirectory, warpedFilePath, aoiwkt, ds)
        print "FOOTPRINT: " + productFootprintWKT
        ds = gdal.Open(warpedFilePath)

        # stretch to bytes
        scaleParams = generic.getScaleParams(ds, 255)
        print "Scale params "
        print(scaleParams)
        outputFilePath = outputDirectory + '/productOutput.tiff'
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

        writeOutput(outputDirectory, "True colour generation using geocento process", [product])

        print "True Colour script finished for PLEIADES product(s) at " + inputDirectory

    elif platformName == 'WORLDVIEW-2':
        # get the tif files
        tiffFiles = findFiles(inputDirectory, 'tif')

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
            tiffFile = panSharpen(outputDirectory, panFiles, msFiles)
        else:
            tiffFile = tiffFiles[0]

        ds = gdal.Open(tiffFile)
        warpedFilePath = outputDirectory + '/warped.vrt'
        productFootprintWKT = generateWarpFile(outputDirectory, warpedFilePath, aoiwkt, ds)
        print "FOOTPRINT: " + productFootprintWKT
        ds = gdal.Open(warpedFilePath)

        # stretch to bytes
        scaleParams = generic.getScaleParams(ds, 255)
        print "Scale params "
        print(scaleParams)
        outputFilePath = outputDirectory + '/productOutput.tiff'
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

        writeOutput(outputDirectory, "True colour generation using geocento process", [product])

        print "Now cleaning up"
        os.remove(tempFilePath)

        print "True Colour script finished for WorldView-2 product(s) at " + inputDirectory

    elif platformName == 'SUPERVIEW':
        # get the tif files
        tiffFiles = findFiles(inputDirectory, ('tiff', 'tif'))

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
            tiffFile = panSharpen(outputDirectory, [panFile], [bandFile])

        ds = gdal.Open(tiffFile)
        warpedFilePath = outputDirectory + '/warped.vrt'
        productFootprintWKT = generateWarpFile(outputDirectory, warpedFilePath, aoiwkt, ds)
        print "FOOTPRINT: " + productFootprintWKT
        ds = gdal.Open(warpedFilePath)

        # stretch to bytes
        scaleParams = generic.getScaleParams(ds, 255)
        print "Scale params "
        print(scaleParams)
        outputFilePath = outputDirectory + '/productOutput.tiff'
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

        writeOutput(outputDirectory, "True colour generation using geocento process", [product])

        print "Now cleaning up"

        print "True Colour script finished for SuperView product(s) at " + inputDirectory

    elif platformName == 'KOMPSAT-2':
        
        start = time.time()
        #Find tiff files
        tiffFilesPaths = findFiles(inputDirectory, ("tif", "tiff"))

        panSharpenFilePath = outputDirectory + "/pansharpen.vrt"
        if len(tiffFilesPaths) == 0:
            sys.exit("No TIFF file in the directory " + inputDirectory)
    
        elif len(tiffFilesPaths) == 1:  #KOMPSAT 2 pansharpened
            print ("Found 1 tiff file.")
            PStiffFilePath = tiffFilesPaths[0]
            path, fileName = os.path.split(PStiffFilePath)
            if "_1G_1MC.TIF" or "_PS.TIF" in fileName.upper():
                # invert bands
                gdal.Translate(panSharpenFilePath, PStiffFilePath, bandList = [3,2,1], format = "VRT")
            else:
                sys.exit("Unable to identify file type.")
            
            
        #Bundle = 1 pan file, 4 MS files - make composite MS image then pansharpen
        elif len(tiffFilesPaths) == 5:
            print ("Found 5 tiff files.")
            #Label the pan and MS files
            bandFilePaths = []
            panFilePathArray = []
    
            #Locate pan file
            for filePath in tiffFilesPaths:
                path, fileName = os.path.split(filePath)
                if "PN" in fileName.upper() and "_1" in fileName.upper():
                    panFilePathArray.append(filePath)
                elif "PP" in fileName.upper() and "_1" in fileName.upper():
                    panFilePathArray.append(filePath)

            #Check the correct number of pan files have been added to the array.
            if len(panFilePathArray) < 1:
                sys.exit("Unable to locate pan file in directory " + inputDirectory)
            elif len(panFilePathArray) > 1:
                sys.exit("More than one pan file found in directory" + inputDirectory)
            else:
                panFilePath = panFilePathArray[0]
    
            #Locate red files
            if not fileType(tiffFilesPaths, "R_1", None, bandFilePaths, 1):
                sys.exit("Error when locating red file.")
    
            #Locate green files
            if not fileType(tiffFilesPaths, "G_1R.TIF", "G_1G.TIF", bandFilePaths, 2):
                sys.exit("Error when locating green file.")
    
            #Locate blue files
            if not fileType(tiffFilesPaths, "B_1", None, bandFilePaths, 3):
                sys.exit("Error when locating blue file.")
    
            #Create composite MS image
            print ("Successfully located pan and MS files. Creating composite colour image.")
            #Create vrt for bands
            colourFilePath = outputDirectory + "/spectral.vrt"
            try:
                gdal.BuildVRT(colourFilePath, bandFilePaths, separate=True)
            except RuntimeError:
                sys.exit("Error with gdal.BuildVRT")
    
            #Now pansharpen
            gdal_pansharpen.gdal_pansharpen(['', panFilePath, colourFilePath, panSharpenFilePath, '-nodata', '0', '-co', 'PHOTOMETRIC=RGB', '-of', 'VRT'])
    
        else:
            sys.exit("Invalid number of files found. " + str(len(tiffFilesPaths)) + " files found in directory " + inputDirectory)
    

        # mark black pixels as transparent
        transparentPanSharpenFilePath = outputDirectory + "/pansharpen_transparent.vrt"
        gdal.BuildVRT(transparentPanSharpenFilePath, panSharpenFilePath, srcNodata = '0', VRTNodata = '0')
        
        ds = gdal.Open(transparentPanSharpenFilePath)
        print "No data value for band 1 " + str(ds.GetRasterBand(1).GetNoDataValue())

        output(transparentPanSharpenFilePath, outputDirectory, aoiwkt, start)
    
        print ("True Colour script finished for Kompsat-2 product(s) at " + inputDirectory)
        totalExecutionTime = time.time()-start
        print ("Total execution time: " + str(totalExecutionTime))
    
    elif platformName == 'KOMPSAT-3':
        
        start = time.time()
        tiffFilesPath = findFiles(inputDirectory, ("tif", "tiff"))
    
        if len(tiffFilesPath) < 1:
            sys.exit("Missing image files in directory " + inputDirectory)
    
        pantileFilePaths = []
        redtileFilePaths = []
        greentileFilePaths = []
        bluetileFilePaths = []
        PRtileFilePaths = []
        PGtileFilePaths = []
        PBtileFilePaths = []
    
        #Label files
        for filePath in tiffFilesPath:
            path, fileName = os.path.split(filePath)
            if "_P_R" in fileName.upper() or "_P.TIF" in fileName.upper(): #This will cause an issue as it'll be picked up by PG
                print ("Image is panchromatic.")
                pantileFilePaths.append(filePath)
            elif "_R_R" in fileName.upper() or "_R.TIF" in fileName.upper():
                print ("Image is red MS file.")
                redtileFilePaths.append(filePath)
            elif "_G_R" in fileName.upper() or "_G.TIF" in fileName.upper():
                print ("Image is green MS file.")
                greentileFilePaths.append(filePath)
            elif "_B_R" in fileName.upper() or "_B.TIF" in fileName.upper():
                print ("Image is blue MS file.")
                bluetileFilePaths.append(filePath)
            elif "_PR_R" in fileName.upper() or "_PR.TIF" in fileName.upper():
                print ("Image is pansharpened red file.")
                PRtileFilePaths.append(filePath)
            elif "_PG_R" in fileName.upper() or "_PG.TIF" in fileName.upper():
                print ("Image is pansharpened green file.")
                PGtileFilePaths.append(filePath)
            elif "_PB_R" in fileName.upper() or "_PB.TIF" in fileName.upper():
                print ("Image is pansharpened blue file.")
                PBtileFilePaths.append(filePath)
    
        #Check for tiles
        panimageFilePath = mosaic(pantileFilePaths, "/panmosaic.vrt", outputDirectory)
        redFilePath = mosaic(redtileFilePaths, "/redmosaic.vrt", outputDirectory)
        greenFilePath = mosaic(greentileFilePaths, "/greenmosaic.vrt", outputDirectory)
        blueFilePath = mosaic(bluetileFilePaths, "/bluemosaic.vrt", outputDirectory)
        PRFilePath = mosaic(PRtileFilePaths, "/PRmosaic.vrt", outputDirectory)
        PGFilePath = mosaic(PGtileFilePaths, "/PGmosaic.vrt", outputDirectory)
        PBFilePath = mosaic(PBtileFilePaths, "/PBmosaic.vrt", outputDirectory)
    
        if redFilePath and greenFilePath and blueFilePath:
            PSFiles = [redFilePath, greenFilePath, blueFilePath]
            #Create composite image from 3 bands
            MSFilePath = outputDirectory + "/MS.vrt"
            gdal.BuildVRT(MSFilePath, PSFiles, separate = True)
    
            if panimageFilePath:
                #Now panSharpen
                finalimageFilePath = outputDirectory + "/pansharpen.vrt"
                gdal_pansharpen.gdal_pansharpen(['', panimageFilePath, MSFilePath, finalimageFilePath, '-nodata', '0', '-co', 'PHOTOMETRIC=RGB', '-of', 'VRT'])
    
            else:
                finalimageFilePath = MSFilePath 
    
        elif PRFilePath and PGFilePath and PBFilePath:
            PSFiles = [PRFilePath, PGFilePath, PBFilePath]
            #Combine 3 bands
            finalimageFilePath = outputDirectory + "/pansharpen.vrt"
            gdal.BuildVRT(finalimageFilePath, PSFiles, separate = True)
        
        else:
            sys.exit("Missing image files in directory " + inputDirectory)
            
        output(finalimageFilePath, outputDirectory, None, start)
    
        print ("True Colour script finished for Kompsat-3 product(s) at " + inputDirectory)
        executiontime = time.time()-start
        print("Total execution time: " + str(executiontime))

    elif platformName == "KOMPSAT-3A":
        
        start = time.time()
        #Find tiff files
        tiffFilePaths = findFiles(inputDirectory, ("tif", "tiff"))
    
        if len(tiffFilePaths) == 0:
            sys.exit("No TIFF file in the directory " + inputDirectory)
    
        elif len(tiffFilePaths) == 4: #Pansharpened KOMPSAT 3A, combine RGB bands into composite image
            print ("Found 4 files")
            PSFiles = []
    
            #Add red files to the array
            if not fileType(tiffFilePaths, "_PR.TIF", None, PSFiles, 1):
                sys.exit("Error when locating red file.")
    
            #Add green files to the array
            if not fileType(tiffFilePaths, "_PG.TIF", None, PSFiles, 2):
                sys.exit("Error when locating green file.")
    
            #Add blue files to the array
            if not fileType(tiffFilePaths, "_PB.TIF", None, PSFiles, 3):
                sys.exit("Error when locating blue file.")
    
            #Create composite PS image from 3 bands
            panSharpenFilePath = outputDirectory + "/pansharpened.vrt"
            gdal.BuildVRT(panSharpenFilePath, PSFiles, separate = True)
    
        #For a bundle
        elif len(tiffFilePaths) == 5: #Bundle = 1 pan file, 4 MS files - make composite MS image then pansharpen
            print ("Found 5 files")
            #Label the pan and MS files
            bandFilePaths = []
            panFilePathArray = []
            #Locate pan files
            if not fileType(tiffFilePaths, "_P.TIF", None, panFilePathArray, 1):
                sys.exit("Error when locating pan file.")
            panFilePath = panFilePathArray[0]
    
            #Locate red files
            if not fileType(tiffFilePaths, "_R.TIF", None, bandFilePaths, 1):
                sys.exit("Error when locating red file.")
    
            #Locate green files
            if not fileType(tiffFilePaths, "_G.TIF", None, bandFilePaths, 2):
                sys.exit("Error when locating green file.")
    
            #Locate blue files
            if not fileType(tiffFilePaths, "_B.TIF", None, bandFilePaths, 3):
                sys.exit("Error when locating blue file.")
    
            #Create composite MS image
            #Create vrt for bands
            colourFilePath = outputDirectory + "/spectral.vrt"
            try:
                gdal.BuildVRT(colourFilePath, bandFilePaths, separate=True)
            except RuntimeError:
                print ("Error with gdal.BuildVRT")
    
            #Now pansharpen
            panSharpenFilePath = outputDirectory + "/pansharpen.vrt"
            gdal_pansharpen.gdal_pansharpen(['', panFilePath, colourFilePath, panSharpenFilePath, '-nodata', '0', '-co', 'PHOTOMETRIC=RGB', '-of', 'VRT'])
    
        else:
            sys.exit("Invalid number of files found. " + len(tiffFilePaths) + " files found in directory " + inputDirectory)
    
        output(panSharpenFilePath, outputDirectory, None, start)
    
        print ("True Colour script finished for Kompsat-3A product(s) at " + inputDirectory)
        executiontime = time.time()-start
        print("Total execution time: " + str(executiontime))

    elif platformName == '_KOMPSAT-2':
        # get the tif files
        tiffFiles = findFiles(inputDirectory, 'tif')

        if len(tiffFiles) == 0:
            sys.exit("Missing TIFF file in directory")

        # create vrt for bands
        panSharpenFilePath = outputDirectory + '/pansharpen.vrt';

        # check if bundle type of product
        if len(tiffFiles) == 2:
            if "_PAN/" in tiffFiles[0]:
                panFile = tiffFiles[0]
                bandFile = tiffFiles[1]
            else:
                panFile = tiffFiles[1]
                bandFile = tiffFiles[0]
            gdal_pansharpen.gdal_pansharpen(['', panFile, bandFile, panSharpenFilePath, '-nodata', '0', '-co', 'PHOTOMETRIC=RGB', '-of', 'VRT'])
        else:
            gdal.Translate(panSharpenFilePath, tiffFiles[0], bandList = [3,2,1], format = 'VRT')

        # warp and stretch the values
        ds = gdal.Open(panSharpenFilePath)
        warpedFilePath = outputDirectory + '/warped.vrt'
        productFootprintWKT = generateWarpFile(outputDirectory, warpedFilePath, aoiwkt, ds)

        scaleParams = generic.getScaleParams(ds, 255)
        print scaleParams
        
        print 'Translating to tiff file'
        
        tempFilePath = outputDirectory + '/temp.tiff'
        ps = gdal.Translate(tempFilePath, warpedFilePath, scaleParams = scaleParams, exponents = [0.5, 0.5, 0.5], outputType = gdal.GDT_Byte, options = ['PHOTOMETRIC=RGB'], format = 'GTiff')
        
        print 'Generate overviews'
        executeOverviews(ps)
        
        print 'Save with overviews'
        outputFilePath = outputDirectory + '/productOutput.tiff'
        gdal.Translate(outputFilePath, ps, format = 'GTiff')

        # now write the output json file
        product = {
            "name": "True colour image",
            "productType": "COVERAGE",
            "SRS":"EPSG:4326",
            "envelopCoordinatesWKT": productFootprintWKT,
            "filePath": outputFilePath,
            "description": "True colour image from Kompsat-2 platform"
        }

        writeOutput(outputDirectory, "True colour generation using geocento process", [product])

        print "Now cleaning up"
        #os.remove(tempFilePath)

        print "True Colour script finished for kompsat-2 product(s) at " + inputDirectory

    elif platformName == '_KOMPSAT-3' or platformName == '_KOMPSAT-3A':
        # get the tif files
        tiffFiles = findFiles(inputDirectory, 'tif')

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
            bandsFilePath = outputDirectory + '/spectral.vrt'
            gdal.BuildVRT(bandsFilePath, bandFiles, separate = True)
            ds = gdal.Open(bandsFilePath)
        else:
            tiffFile = tiffFiles[0]

        warpedFilePath = outputDirectory + '/warped.vrt'
        #ds = gdal.Warp(warpedFilePath, bandsFilePath, format = 'VRT', dstSRS = 'EPSG:4326')
        productFootprintWKT = generateWarpFile(outputDirectory, warpedFilePath, aoiwkt, ds)
        #productFootprintWKT = aoiwkt

        scaleParams = generic.getScaleParams(ds, 255)
        print scaleParams
        
        print 'Translating to tiff file'
        
        tempFilePath = outputDirectory + '/temp.tiff'
        ps = gdal.Translate(tempFilePath, warpedFilePath, scaleParams = scaleParams, outputType = gdal.GDT_Byte, options = ['PHOTOMETRIC=RGB'], format = 'GTiff')
        
        print 'Generate overviews'
        executeOverviews(ps)
        
        print 'Save with overviews'
        outputFilePath = outputDirectory + '/productOutput.tiff'
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

        writeOutput(outputDirectory, "True colour generation using geocento process", [product])

        print "True Colour script finished for kompsat-3 product(s) at " + inputDirectory

    elif platformName == 'PLANETSCOPE':
        # get the tif files
        tifFiles = findFiles(inputDirectory, 'tif')

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
        tempFilePath = outputDirectory + '/temp.tiff';
        outputFilePath = outputDirectory + '/productOutput.tiff'
        # if analytics we need to do some scaling for contrasts and reshuffle and reduce bands
        if analytic:
            # reshuffle and reduce bands
            ds = gdal.Translate('temp', ds, format = 'MEM', bandList = [3,2,1])
            print "Analytic product, modifying contrast for visualisation"
            scaleParams = generic.getScaleParams(ds, 255)
            print "Scale params "
            print(scaleParams)
            ds = gdal.Translate('temp', ds, format = 'MEM', scaleParams = scaleParams, exponents = [0.5, 0.5, 0.5])
        
        ds = gdal.Warp('temp', ds, format = 'GTiff', srcNodata = 0, dstAlpha = True, dstSRS = 'EPSG:4326')
        productFootprintWKT = getFootprintPath(aoiwkt, ds)
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
            "description": "True colour image from PlanetScope platform"
        }

        writeOutput(outputDirectory, "True colour generation using geocento process", [product])

        print "True Colour script finished for TRIPPLE SAT product(s) at " + inputDirectory

    elif platformName == 'SENTINEL1':
        pass
    else:
        sys.exit("Unknown platform " + platformName)
        
def generateWarpFile(outputDirectory, warpedFilePath, aoiwkt, ds):
    footprintGeometryWKT = generic.getDatasetFootprint(ds)
    if aoiwkt is not None:
        gdal.SetConfigOption('GDALWARP_DENSIFY_CUTLINE', 'NO')
        intersectionWKT = generic.calculateCutline(footprintGeometryWKT, aoiwkt)
        print "FOOTPRINT: " + footprintGeometryWKT
        print "AOI: " + aoiwkt
        print "INTERSECTION: " + intersectionWKT
        
        csvFileDirectory = outputDirectory
        csvFilePath = generic.createCutline(csvFileDirectory, intersectionWKT)
        
        gdal.Warp(warpedFilePath, ds, format = 'VRT', cutlineDSName = csvFilePath, srcNodata = 0, dstAlpha = True, cropToCutline = True, dstSRS = 'EPSG:4326', warpOptions = ['GDALWARP_DENSIFY_CUTLINE=NO'])
        
        return intersectionWKT
    else:
        gdal.Warp(warpedFilePath, ds, format = 'VRT', srcNodata = 0, dstAlpha = True, dstSRS = 'EPSG:4326')
        return footprintGeometryWKT

def getFootprintPath(aoiwkt, ds):
    footprintGeometryWKT = generic.getDatasetFootprint(ds)
    if aoiwkt is not None:
        intersectionWKT = generic.calculateCutline(footprintGeometryWKT, aoiwkt)
        return intersectionWKT
    else:
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

def warpTranslateOverview(panSharpenFilePath, outputDirectory, aoiwkt):
    ds = gdal.Open(panSharpenFilePath)

    warpedFilePath = outputDirectory + '/warped.vrt'
    productFootprintWKT = generateWarpFile(outputDirectory, warpedFilePath, aoiwkt, ds)

    scaleParams = generic.getScaleParams(ds, 255)
    print scaleParams

    print 'Translating to tiff file'
    
    # check size of image
    fileSize = ds.RasterXSize * ds.RasterYSize
    localOperation = fileSize > 10000 * 10000
    tempFile = outputDirectory + "/temp.tif"
    if localOperation:
        ps = gdal.Translate(tempFile, warpedFilePath, scaleParams = scaleParams, outputType = gdal.GDT_Byte, options = ['PHOTOMETRIC=RGB'], format = 'GTIFF')
    else:
        ps = gdal.Translate("temp", warpedFilePath, scaleParams = scaleParams, exponents = [0.5, 0.5, 0.5], outputType = gdal.GDT_Byte, options = ['PHOTOMETRIC=RGB'], format = 'MEM')
    
    print 'Generate overviews'
    executeOverviews(ps)
    
    print 'Save with overviews'
    outputFilePath = outputDirectory + '/productOutput.tiff'
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

def panSharpen(outputDirectory, panFiles, bandFiles):

    # create VRT with the files
    if len(panFiles) == 1:
        panFilePath = panFiles[0]
    elif len(panFiles) > 1:
        # mosaic the tif files
        panFilePath = outputDirectory + '/panfiles.vrt'
        gdal.BuildVRT(panFilePath, panFiles)
    else:
        sys.exit('No pan files')
    
    if len(bandFiles) == 1:
        bandsFilePath = bandFiles[0]
    elif len(bandFiles) == 3:
        # assumes bands are in the right order
        bandsFilePath = outputDirectory + '/spectral.vrt'
        gdal.BuildVRT(bandsFilePath, bandFiles, separate = True)
    else:
        sys.exit('No pan files')
    
    panSharpenFilePath = outputDirectory + '/pansharpen.vrt';

    gdal_pansharpen.gdal_pansharpen(['', panFilePath, bandsFilePath, panSharpenFilePath, '-nodata', '0', '-co', 'PHOTOMETRIC=RGB', '-of', 'VRT'])

    if not os.path.exists(panSharpenFilePath):
        sys.exit("Pansharpen failed, no file at " + panSharpenFilePath)
        
    return panSharpenFilePath

def fileType(filesPathArray, string, string2, outputArray, expectedLength):
    returnStatus = True
    for filePath in filesPathArray:
        path, fileName = os.path.split(filePath)
        if string and string2:
            if string in fileName.upper():
                outputArray.append(filePath)
            elif string2 in fileName.upper():
                outputArray.append(filePath)
        elif string:
            if string in fileName.upper():
                outputArray.append(filePath)
        else:
            print ("Missing string.")
    # Check the correct number of files have been added to the array.
    if len(outputArray) < expectedLength:
        returnStatus = False
        if string and string2:
            print ("Unable to locate file with " + string + " or " + string2 + " in filename.")
        elif string:
            print ("Unable to locate file with " + string + " in filename.")
    elif len(outputArray) > expectedLength:
        returnStatus = False
        if string and string2:
            print ("More than one file with " + string + " or " + string2 + " in filename.")
        elif string:
            print ("More than one file with " + string + " in filename.")
    return returnStatus
    
def mosaic(filePathsArray, fileName, outputDirectory):
    if len(filePathsArray) > 1: #If there is more than one pan file, mosaic the tiles.
        filePath = outputDirectory + fileName
        gdal.BuildVRT(filePath, filePathsArray)
        print ("Mosaic complete.")
    elif len(filePathsArray) == 1:
        filePath = outputDirectory + fileName
        #Convert to vrt format.
        gdal.Translate(filePath, filePathsArray[0], format = "VRT")
        print ("No mosaic necessary.")
    else:
        filePath = False
    return filePath

def output(imageFilePath, outputDirectory, aoiwkt, start):
    
    ds = gdal.Open(imageFilePath)

    #Reproject and extract footprint
    warpedFilePath = outputDirectory + '/warped.vrt'
    productFootprintWKT = generateWarpFile(outputDirectory, warpedFilePath, aoiwkt, ds)
    print "FOOTPRINT: " + productFootprintWKT
    ds = gdal.Open(warpedFilePath)

    # expects bands to be in the right order
    scaleParams = generic.getScaleParams(ds, 255, [1,2,3])
    print ("Scale params: " + str(scaleParams))

    #Convert to tiff file with 3 bands only.
    print ("Translating to tiff file.")
    beforeTranslateTime = time.time() - start
    ds = gdal.Translate("temp", ds, scaleParams = scaleParams, exponents = [0.5, 0.5, 0.5], outputType = gdal.GDT_Byte, options = ["PHOTOMETRIC=RGB"], format = "MEM")
    afterTranslateTime = time.time() - start
    print ("Translate execution time: " + str(afterTranslateTime-beforeTranslateTime))

    #Create overlays
    print ("Generate overviews.")
    executeOverviews(ds)

    print ("Save with overviews.")
    outputFilePath = outputDirectory + "/productOutput.tiff"
    gdal.Translate(outputFilePath, ds, format = 'GTiff')

    # now write the output json file, for EI Neo
    product = {
        "name": "True colour image",
        "productType": "COVERAGE",
        "SRS":"EPSG:4326",
        "envelopCoordinatesWKT": productFootprintWKT,
        "filePath": outputFilePath,
        "description": "True colour image from Kompsat-2 platform"
    }

    generic.writeOutput(outputDirectory, "True colour generation using geocento process", [product])

def main():
    return trueColour(sys.argv)

if __name__ == '__main__':
    sys.exit(trueColour(sys.argv))
