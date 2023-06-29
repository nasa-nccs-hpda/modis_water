<div style="font-size:14px; font-family:verdana;">

# <b>MODIS Water - MOD44W Classifier Application Documentation</b>

Version 4.0.1

Data Science Group 606.3

<br/>

- [MODIS Water - MOD44W Classifier Application Documentation](#modis-water---mod44w-classifier-application-documentation)
  - [4.0.1 Changelog](#400-changelog)
    - [OLD (DO NOT USE THIS)](#old-do-not-use-this)
    - [NEW (USE THIS INSTEAD)](#new-use-this-instead)
  - [Overview](#overview)
  - [Installation](#installation)
    - [Installing with a singularity container](#installing-with-a-singularity-container)
    - [Installing with git](#installing-with-git)
    - [ Dependencies ](#-dependencies-)
    - [ Data Staging ](#-data-staging-)
      - [ Expected data products ](#-expected-data-products-)
        - [MOD09GA and MOD09GQ](#mod09ga-and-mod09gq)
        - [MCD64A1](#mcd64a1)
      - [Staged data products](#staged-data-products)
        - [Post-processing product](#post-processing-product)
  - [ User Guide ](#-user-guide-)
    - [ MODIS water application command line invocations](#-modis-water-application-command-line-invocations)
      - [Running with multiple sensors](#running-with-multiple-sensors)
    - [ Running modis\_water with a container ](#-running-modis_water-with-a-container-)
    - [ Running modis\_water without a container ](#-running-modis_water-without-a-container-)
    - [ Runtime expectations ](#-runtime-expectations-)
    - [Output Data Products](#output-data-products)
    - [ Wrapping to HDF ](#-wrapping-to-hdf-)
  - [ Appendix A. ](#-appendix-a-)
  - [ Appendix B. Testing ](#-appendix-b-testing-)
    - [ Unit-test ](#-unit-test-)
    - [ Full Run ](#-full-run-)

## <b>4.0.1 Changelog</b>

4.0.1 BUGFIX: Removed bug from impervious map generation (which is added to the packed bit post-processing mask) which included no-data in the impervious land flip. Updated post-processing masks are required.

As with the 4.0.0 change, GMTED/DEM products and Static Seven Class products are no longer supported. Instead a single post-processing product is required.
See the "Staged data products" section for more information on the post-processing product.

NO LONGER NEEDED:
`MODIS_GMTED_DEM_slope, MODIS_Seven_Class_maxextent`

```
/explore/nobackup/projects/ilab/data/MODIS/ancillary/MODIS_GMTED_DEM_slope
/explore/nobackup/projects/ilab/data/MODIS/ancillary/MODIS_Seven_Class_maxextent
```

NOW NEEDED:
`postprocessing_dir`

```
/explore/nobackup/projects/ilab/data/MODIS/ancillary/postprocess_dir
```

RF algorithm is no longer meant to be used. Simple algorithm is the algorithm to use in production. This is a simple switch of
the `--classifier` command-line argument from `rf` to `simple`.

### OLD (DO NOT USE THIS)

```shell
$ python <path_modis_water_code_base>/modis_water/view/EndToEndModisWaterCLV.py \
    --classifier rf \
    -t h09v05 \
    -y 2006 \
    -sensor MOD \
    -static /path/to/static/seven_class \
    -dem /path/to/gmted/dem/slope \
    -mod /path/modis/Collection6.1/L2G \
    -burn /path/modis/Collection6/L3/MCD64A1-BurnArea \
    -o /path/to/output/directory
```

### NEW (USE THIS INSTEAD)

```shell
$ python <path_modis_water_code_base>/modis_water/view/EndToEndModisWaterCLV.py \
    --classifier simple \
    -t h09v05 \
    -y 2006 \
    -sensor MOD \
    -postprocessing /path/to/postprocessing_dir/ \
    -mod /path/modis/Collection6.1/L2G \
    -burn /path/modis/Collection6/L3/MCD64A1-BurnArea \
    -o /path/to/output/directory
```

## <b>Overview</b>

This documentation shows how to run the MODIS Water MOD44W Version 7 annual water mask
generation application. The MOD44W Version 7 is derived using a random forest classifier
trained with MODIS data and validated with the Version 6 MOD44W data product. The annual
water mask product (MOD44W) is derived from combining individual day water mask predictions.
The input for the random forest classifier in order to generate the individual day water
mask prediction is the MOD09GA and MOD09GQ data products. Once the individual day water
mask predictions have been predicted, the annual product is generated. This is the unprocessed
result. Once the annual product has been generated, the result is processed with input from
external products to generate a corresponding pixel by pixel quality assurance layer.
After the annual product is post-processed, a seven-class product is generated.

<br/>

## <b>Installation</b>

Get started with modis_water to generate MOD44W annual products.

<br/>

### <b>Installing with a singularity container</b>

Installing the singularity software is out of scope of this documentation. See <https://singularity-docs.readthedocs.io/en/latest/> for guidance on installing singularity.

<b> Pulling the singularity container </b>

```shell
singularity pull oras://gitlab.nccs.nasa.gov:5050/cisto-ilab/containers/modis_water:4.0.0
```

```
INFO:    Downloading oras image
```

A `.sif` file should have been downloaded:

```shell
ls
```

```
modis_water_4.0.0.sif
```

<br/>

### <b>Installing with git</b>

The codebase can be downloaded via git. These are private repositories, please contact the main point of contact to be granted access to clone via git. There are two git repositories that are necessary to run the MOD44W product generation.

<br/>

<b>ILAB's modis_water</b>: <https://github.com/nasa-nccs-hpda/modis_water>

```shell
git clone git@github.com:nasa-nccs-hpda/modis_water.git
```

```shell
Cloning into 'modis_water'...
remote: Enumerating objects: 184, done.
remote: Counting objects: 100% (184/184), done.
remote: Compressing objects: 100% (126/126), done.
remote: Total 184 (delta 70), reused 162 (delta 51), pack-reused 0
Receiving objects: 100% (184/184), 60.48 MiB | 50.24 MiB/s, done.
Resolving deltas: 100% (70/70), done.
```

<br/>

<b>ILAB's core repository</b>: <https://github.com/nasa-nccs-hpda/core>

```shell
git clone git@github.com:nasa-nccs-hpda/core.git
```

```shell
Cloning into 'core'...
remote: Enumerating objects: 380, done.
remote: Counting objects: 100% (380/380), done.
remote: Compressing objects: 100% (250/250), done.
remote: Total 380 (delta 199), reused 302 (delta 121), pack-reused 0
Receiving objects: 100% (380/380), 2.51 MiB | 0 bytes/s, done.
Resolving deltas: 100% (199/199), done.
```

See Appendix A. for the module map of the modis_water application source code. 

<br/>

### <b> Dependencies </b>

Dependencies are not necessary to deal with if using the singularity container. However if installing and running from source, use the definition file of the container to determine python and unix dependencies.

```shell
$ git clone git@github.com:nasa-nccs-hpda/modis_water.git
$ cat modis_water/container/modis-water-4.0.0.def
```

<br/>

### <b> Data Staging </b>

The modis_water application requires various data products to derive the MOD44W product. We will separate these into two parts. The first part is the data presumably available in the MODAPS environment. The second are custom data products developed by ILAB that will need to be staged.

#### <b> Expected data products </b>

- `MOD09GA`
- `MOD09GQ`
- `MCD64A1`

##### <b>MOD09GA and MOD09GQ</b>

The modis_water application expects these data products to be in a certain directory structure, as such:

```
<base_path>/MOD09G<Q/A>/<year>/MOD09G<Q/A>.A<year><jday>.<tile>.*.hdf
```

```
<BASE-PATH>
|
|--MOD09GA
|    |
|    |-- 2001
|         |
|         |--MOD09GA.A2001365.h12v09.061.2020067154930.hdf
|--MOD09GQ
     |
     |--2001
         |
         |--MOD09GQ.A2001365.h21v10.061.2020067155113.hdf
```

##### <b>MCD64A1</b>

The modis_water application expects this data product to be in a certain directory structure as such:

```
<base_path>/<year>/<julian_day>/MCD64A1.A<year><jday>.<tile>.*.hdf
```

```
<BASE-PATH>
|
|--2001
|    |
|    |--032
|         |
|         |--MCD64A1.A2001032.h09v05.006.2017012055352.hdf
|--2002
     |
     |--213
         |
         |--MCD64A1.A2002213.h09v05.006.2017013113729.hdf
```

#### <b>Staged data products</b>

- Post-processing product

##### <b>Post-processing product</b>

This product is a packed-bit product which contains several post-processing
products used by the MODIS water application to perform post-processing of
the initial water masks generated by the algorithm.

Explore Location:

```
/explore/nobackup/projects/ilab/data/MODIS/ancillary/postprocess_dir
```

| Characteristic      | Description                        |
| ------------------- |:-----------------------------------|
| Product             | Post-processing product for MW     |
| File type           | GeoTIFF                            |
| File Size           | `44M`               |
| Spatial Extent      | MODIS Sinusoidal Tile              |
| Coordinate System   | Sinusoidal                         |
| Number of bands     | 1                                  |
| Pixel Resolution    | 231.656350000000003                |
| Columns/Rows        | 4800x4800                          |
| Pixel Value Type    | Uint16                             |

The modis_water application expects this data product to be in a certain directory structure as such:

```shell
<post-processing dir>/postprocess_water_h32v07.tif
```

## <b> User Guide </b>

The modis_water application contains one command-line interface (CLI). This CLI will invoke the modis_water application, create daily predictions, create the annual pre-processed water mask product. From this, the calculate annual water mask is processed, a quality assurance (QA) product is output, an annual accumulation of the MCD64A1 is output, along with the seven-class product derived from the processed MOD44W product.

### <b> MODIS water application command line invocations</b>

```shell
$ python <path_modis_water_code_base>/modis_water/view/EndToEndModisWaterCLV.py \
    --classifier {simple,rf} \
    [--debug] \
    [--startDay 1-365] \
    [--endDay 1-365] \
    [--georeferenced] \
    -postprocessing <PATH TO POST PROCESSING PRODUCT> \
    -mod <PATH TO MOD09GA/GQ DATA PRODUCT> \
    -burn <PATH TO MCD64A1 BURN SCAR DATA PRODUCT> \
    -t <TILE TO PROCESS; FORMAT h##v##> \
    -y <YEAR TO PROCESS> \
    [-o .]
```

| Command-line-argument | Description                                         |Required/Optional/Flag | Default  | Example                  |
| --------------------- |:----------------------------------------------------|:---------|:---------|:--------------------------------------|
| `--classifier`        | Which classifier to use. rf represents our latest trained Random Forest classifier, use this.                           | Required | N/a      |`--classifier rf`                      |
| `--debug`             | Show extra output and write <br> intermediate files.| Flag     | N/a      |`--debug`                              |
| `-t`                  | Tile to process; format h##v##.                     | Required | N/a      |`-t h09v05`                            |
| `-y`                  | Year to process.                                    | Required | N/a      |`-y 2006`                              |
| `--sensor`            | Which sensor to run the model on. [MOD / MYD]       | Optional | MOD MYD  | `--sensor MOD` |
| `--georeferenced`     | Write products out with geospatial <br> information.| Flag     | N/a      |`--georeferenced`                      |
| `-postprocessing`     | Path to post-processing <br> product.               | Required | N/a      |`-static /path/to/postprocessing_dir/` |
| `-mod`                | Path to MODIS MOD09GA and MOD09GQ products.         | Required | N/a      |`-mod /path/modis/Collection6.1/L2G`   |
| `-burn`               | PATH TO MCD64A1 burn scar product.                  | Required | N/a      |`-burn /path/modis/Collection6/L3/MCD64A1-BurnArea` |
| `-o`                  | Output directory.                                   | Optional | `.`      |`-o /path/to/output/directory`         |

Example

```shell
$ python <path_modis_water_code_base>/modis_water/view/EndToEndModisWaterCLV.py \
    --classifier simple \
    -t h09v05 \
    -y 2006 \
    -sensor MOD \
    -postprocessing /path/to/postprocessing_dir/ \
    -mod /path/modis/Collection6.1/L2G \
    -burn /path/modis/Collection6/L3/MCD64A1-BurnArea \
    -o /path/to/output/directory
```

#### Running with multiple sensors

```shell
$ python <path_modis_water_code_base>/modis_water/view/EndToEndModisWaterCLV.py \
    --classifier simple \
    -t h09v05 \
    -y 2006 \
    -sensor MOD MYD \
    -postprocessing /path/to/postprocessing_dir/ \
    -mod /path/modis/Collection6.1/L2G \
    -burn /path/modis/Collection6/L3/MCD64A1-BurnArea \
    -o /path/to/output/directory
```

### <b> Running modis_water with a container </b>

To execute the modis_water application with a container, you can use the `singularity exec`. Any singularity execution, you need to list the drives to mount to the container.

```shell
$ singularity exec -B <DRIVE-TO-MOUNT-0>,<DRIVE-TO-MOUNT-1> <PATH-TO-CONTAINER> COMMAND
```

For example, in NCCS ADAPT, we need to mount our central storage and networked file system.

```shell
$ singularity exec -B /explore,/panfs,/css,/nfs4m modis_water_4.0.0.sif COMMAND
```

Executing the modis_water application follow these conventions:

```shell
$ singularity exec -B <DRIVE-TO-MOUNT-0>,<DRIVE-TO-MOUNT-1> <PATH-TO-CONTAINER> \ 
    python <PATH-TO-MW-CODE>/modis_water/view/EndToEndModisWaterCLV.py \
    --classifier {simple,rf} \
    [--debug] \
    [--sensor MOD MYD] \
    [--georeferenced] \
    -t <TILE TO PROCESS; FORMAT h##v##> \
    -y <YEAR TO PROCESS> \
    -postprocessing <PATH TO POST-PROCESSING PRODUCT> \
    -mod <PATH TO MOD09GA/GQ DATA PRODUCT> \
    -burn <PATH TO MCD64A1 BURN SCAR DATA PRODUCT> \
    -o <OUTPUT DIRECTORY>
```

An example:

```shell
$ singularity exec -B /explore,/panfs,/css,/nfs4m modis_water_3.0.1.sif \
    python /usr/local/ilab/modis_water/view/EndToEndModisWaterCLV.py \
    --classifier simple \
    -t h09v05 \
    -y 2006 \
    --sensor MOD \
    -postprocessing /explore/nobackup/projects/ilab/data/MODIS/ancillary/postprocess_dir \
    -mod /css/modis/Collection6.1/L2G \
    -burn /css/modis/Collection6/L3/MCD64A1-BurnArea \
    -o .
```

### <b> Running modis_water without a container </b>

To execute the modis_water application without a container, make sure you have all the dependencies listed in the current python environment. You will also need to set the `PYTHONPATH` to point to the location of the `modis_water` code base and the `core` code base that you've cloned with git.

For example, if `modis_water` and `core` are in your current working directory:

```shell
$ export PYTHONPATH="$PWD:$PWD/modis_water:$PWD/core"
```

Or if you want to export to an absolute path:

```shell
$ export PYTHONPATH="/path/to/pwd:/path/to/pwd/modis_water:/path/to/pwd/core"
```

Once `PYTHONPATH` is set. You can then run the modis_water application. Example:

```shell
$ python modis_water/view/EndToEndModisWaterCLV.py \
    --classifier simple \
    -t h09v05 \
    -y 2006 \
    --sensor MOD \
    -postprocessing /explore/nobackup/projects/ilab/data/MODIS/ancillary/postprocess_dir \
    -mod /css/modis/Collection6.1/L2G \
    -burn /css/modis/Collection6/L3/MCD64A1-BurnArea \
    -o .
```

### <b> Runtime expectations </b>

Expect runtime warnings while the application is running. These are expected and handled. Some examples of warnings expected are:

- sklearn pickle version compatibility
- divide by zero encountered

Example of output:

```shell
Reading MOD tile h09v05 for day 1
Creating output/2006-001-h09v05-MOD-RandomForest.tif
Generating mask
Classifying
Masking
Reading MOD tile h09v05 for day 2
Creating output/2006-002-h09v05-MOD-RandomForest.tif
Generating mask
Classifying
Masking
...
Reading MOD tile h09v05 for day 365
Creating output/2006-365-h09v05-MOD-RandomForest.tif
Generating mask
Classifying
Masking
Creating annual map.
Creating annual burn scar map.
Wrote annual burn scar map to: output/MOD.A2006.h09v05.Simple.AnnualBurnScar.20220901150.tif
Post processing.
Wrote annual QA products to: output/MOD44W.A2006.h09v05.Simple.AnnualWaterProduct.20220901150.bin
Wrote annual QA products to: output/MOD44W.A2006.h09v05.Simple.AnnualWaterProductQA.20220901150.bin
Wrote annual seven class to: output/MOD44W.A2006.h09v05.Simple.AnnualSevenClass.20220901150.bin
```

### <b>Output Data Products</b>

There will be intermediate and final output data products in the output directory.

| Product                                                | Description           |  Intermediate/Final  | Example  |
| ------------------------------------------------------ |:----------------------| :------------------- |:---------|
| `<YEAR>-<JDAY>-<TILE>-MOD-<CLASSIFIER>.tif`| Intermediate single-day prediction|Intermediate|  2006-363-h09v05-MOD-RandomForest.tif|
| `<YEAR>-<TILE>-MOD-<CLASSIFIER>-Mask.tif`| Pre-processed annual product   | Intermediate | 2006-h09v05-MOD-RandomForest-Mask.tif | 
| `<YEAR>-<TILE>-MOD-<CLASSIFIER>-ProbWater.tif`| Probability of water   | Intermediate | 2006-h09v05-MOD-RandomForest-ProbWater.tif | 
| `<YEAR>-<TILE>-MOD-<CLASSIFIER>-SumLand.tif`| Sum of land observation   | Intermediate | 2006-h09v05-MOD-RandomForest-SumLand.tif | 
| `<YEAR>-<TILE>-MOD-<CLASSIFIER>-SumObs.tif`    | Sum of observations   | Intermediate | 2006-h09v05-MOD-RandomForest-SumObs.tif | 
| `<YEAR>-<TILE>-MOD-<CLASSIFIER>-SumWater.tif`    | Sum of water observations  | Intermediate | 2006-h09v05-MOD-RandomForest-SumWater.tif | 
| `MOD.A<YEAR>.<TILE>.<CLASSIFIER>.AnnualBurnScar.*.tif`| Annual summation of MCD64A1 product  | Intermediate | MOD.A2006.h09v05.RandomForest.AnnualBurnScar.20220901150.tif | 
|  `MOD44W.A<YEAR>.<TILE>.<CLASSIFIER>.AnnualWaterProduct.*.tif`| MOD44W final product | Final | MOD44W.A2006.h09v05.RandomForest.AnnualWaterProduct.20220901150.tif | 
| `MOD44W.A<YEAR>.<TILE>.<CLASSIFIER>.AnnualWaterProductQA.*.tif`  | Quality Assurance for MOD44W  | Final | MOD44W.A2006.h09v05.RandomForest.AnnualWaterProductQA.20220901150.tif | 
| `MOD44W.A<YEAR>.<TILE>.<CLASSIFIER>.AnnualSevenClass.*.tif`  | Seven-class derived from MOD44W  | Final | MOD44W.A2006.h09v05.RandomForest.AnnualSevenClass.20220901150.tif | 

### <b> Wrapping to HDF </b>

The final products will need to wrapped into the final HDF format. Only the three final products will need to be wrapped. In this order:

1. MOD44W Product: `MOD44W.A2006.h09v05.RandomForest.AnnualWaterProduct.20220901150.tif`
2. MOD44W Seven Class Product: `MOD44W.A2006.h09v05.RandomForest.AnnualSevenClass.20220901150.tif`
3. MOD44W QA Product: `MOD44W.A2006.h09v05.RandomForest.AnnualWaterProductQA.20220901150.tif`

## <b> Appendix A. </b>

```

modis_water
          |
          |--view
          |     |-EndToEndModisWaterCLV.py
          |
          |--model
                 |
                 |--AnnualMap.py
                 |--BandReader.py
                 |--BurnScarMap.py
                 |--Classifier.py
                 |--ImperviousMap.py
                 |--MaskGenerator.py
                 |--QAMap.py
                 |--RandomForestClassifier.py
                 |--RandomForestModel.sav
                 |--SevenClass.py
                 |--SimpleClassifier.py
                 |--Utils.py
                 |--__init__.py
                 |--tests
                        |
                        |--test_BandReader.py
                        |--test_BurnScarMap.py
                        |--test_ImperviousMap.py
                        |--test_MaskGenerator.py
                        |--test_QAMap.py
                        |--__init__.py
```

## <b> Appendix B. Testing </b>

To test the functionality of the production container there will be two tests. The first is a simple unittest. The second is a full run. Expect the second test to run for at least 15 minutes.

### <b> Unit-test </b>
```shell
$ singularity exec -B /explore,/panfs,/css,/nfs4m \
  /explore/nobackup/people/iluser/ilab_containers/modis_water_4.0.0.sif \
  python -m unittest discover /usr/local/ilab/modis_water/model/tests
```
Expected output:

```shell
bandDict: {'SensorZenith_1': array([[5983, 5983, 5983, ..., 1126, 1126, 1126],
       [5983, 5983, 5983, ..., 1126, 1126, 1126],
       [5983, 5983, 5983, ..., 1126, 1126, 1126],
       ...,
       [3659, 3659, 3659, ..., 5324, 5324, 5324],
       [3659, 3659, 3659, ..., 5324, 5324, 5324],
       [3659, 3659, 3659, ..., 5324, 5324, 5324]], dtype=int16), 'sur_refl_b01_1': array([[1665, 1845, 1845, ..., 1254, 1005,  442],
       [1867, 1971, 1971, ..., 1018,  442,  316],
       [2062, 1971, 1995, ...,  476,  310,  522],
       ...,
       [1193, 1383, 1243, ..., 6233, 6180, 5999],
       [1130, 1149, 1149, ..., 7213, 7083, 6791],
       [1075, 1293, 1338, ..., 7083, 7083, 6791]], dtype=int16)}
..MCD64A1 not found for h20v00. Using empty burn scar product.
MCD64A1 not found for h20v00. Using empty burn scar product.
Wrote annual burn scar map to: /explore/nobackup/people/cssprad1/.nccstmp/MOD.A2020.h20v00.rf.AnnualBurnScar.20230951312.tif
Wrote annual burn scar map to: /explore/nobackup/people/cssprad1/.nccstmp/MOD.A2020.h20v00.rf.AnnualBurnScar.20230951312.tif
MCD64A1 not found for h16v01. Using empty burn scar product.
MCD64A1 not found for h16v01. Using empty burn scar product.
Wrote annual burn scar map to: /explore/nobackup/people/cssprad1/.nccstmp/MOD.A2020.h16v01.rf.AnnualBurnScar.20230951312.tif
Wrote annual burn scar map to: /explore/nobackup/people/cssprad1/.nccstmp/MOD.A2020.h16v01.rf.AnnualBurnScar.20230951312.tif
MCD64A1 not found for h15v14. Using empty burn scar product.
MCD64A1 not found for h15v14. Using empty burn scar product.
Wrote annual burn scar map to: /explore/nobackup/people/cssprad1/.nccstmp/MOD.A2020.h15v14.rf.AnnualBurnScar.20230951312.tif
Wrote annual burn scar map to: /explore/nobackup/people/cssprad1/.nccstmp/MOD.A2020.h15v14.rf.AnnualBurnScar.20230951312.tif
MCD64A1 not found for h13v15. Using empty burn scar product.
MCD64A1 not found for h13v15. Using empty burn scar product.
Wrote annual burn scar map to: /explore/nobackup/people/cssprad1/.nccstmp/MOD.A2020.h13v15.rf.AnnualBurnScar.20230951312.tif
Wrote annual burn scar map to: /explore/nobackup/people/cssprad1/.nccstmp/MOD.A2020.h13v15.rf.AnnualBurnScar.20230951312.tif
MCD64A1 not found for h13v16. Using empty burn scar product.
MCD64A1 not found for h13v16. Using empty burn scar product.
Wrote annual burn scar map to: /explore/nobackup/people/cssprad1/.nccstmp/MOD.A2020.h13v16.rf.AnnualBurnScar.20230951312.tif
Wrote annual burn scar map to: /explore/nobackup/people/cssprad1/.nccstmp/MOD.A2020.h13v16.rf.AnnualBurnScar.20230951312.tif
MCD64A1 not found for h13v17. Using empty burn scar product.
MCD64A1 not found for h13v17. Using empty burn scar product.
Wrote annual burn scar map to: /explore/nobackup/people/cssprad1/.nccstmp/MOD.A2020.h13v17.rf.AnnualBurnScar.20230951312.tif
Wrote annual burn scar map to: /explore/nobackup/people/cssprad1/.nccstmp/MOD.A2020.h13v17.rf.AnnualBurnScar.20230951312.tif
.........
----------------------------------------------------------------------
Ran 11 tests in 7.146s

OK
```

### <b> Full Run </b>

```shell
$ singularity exec -B /explore,/panfs,/css,/nfs4m \
    /explore/nobackup/people/iluser/ilab_containers/modis_water_4.0.0.sif \
    python /usr/local/ilab/modis_water/view/EndToEndModisWaterCLV.py \
    --classifier simple \
    -t h28v14 \
    -y 2019 \
    --sensor MYD \
    -postprocessing /explore/nobackup/projects/ilab/data/MODIS/ancillary/MODIS_Seven_Class_maxextent \
    -mod /css/modis/Collection6.1/L2G \
    -burn /css/modis/Collection6/L3/MCD64A1-BurnArea \
    -o .
```

Expected output:

```shell
...
2023-04-05 10:50:39; INFO; Generating mask
2023-04-05 10:50:40; INFO; Classifiying
2023-04-05 10:50:40; INFO; Masking
2023-04-05 10:50:41; INFO; Reading MYD tile h28v14 for day 355
2023-04-05 10:50:41; INFO; Creating data/2019/h28v14/2019-355-h28v14-MYD-Simple.tif
2023-04-05 10:50:44; INFO; Generating mask
2023-04-05 10:50:45; INFO; Classifiying
2023-04-05 10:50:45; INFO; Masking
2023-04-05 10:50:46; INFO; Reading MYD tile h28v14 for day 356
2023-04-05 10:50:46; INFO; Creating data/2019/h28v14/2019-356-h28v14-MYD-Simple.tif
2023-04-05 10:50:49; INFO; Generating mask
2023-04-05 10:50:49; INFO; Classifiying
2023-04-05 10:50:50; INFO; Masking
2023-04-05 10:50:50; INFO; Reading MYD tile h28v14 for day 357
2023-04-05 10:50:50; INFO; Creating data/2019/h28v14/2019-357-h28v14-MYD-Simple.tif
2023-04-05 10:50:53; INFO; Generating mask
2023-04-05 10:50:54; INFO; Classifiying
2023-04-05 10:50:54; INFO; Masking
2023-04-05 10:50:55; INFO; Reading MYD tile h28v14 for day 358
2023-04-05 10:50:55; INFO; Creating data/2019/h28v14/2019-358-h28v14-MYD-Simple.tif
2023-04-05 10:50:58; INFO; Generating mask
2023-04-05 10:50:58; INFO; Classifiying
2023-04-05 10:50:59; INFO; Masking
2023-04-05 10:50:59; INFO; Reading MYD tile h28v14 for day 359
2023-04-05 10:50:59; INFO; Creating data/2019/h28v14/2019-359-h28v14-MYD-Simple.tif
2023-04-05 10:51:02; INFO; Generating mask
2023-04-05 10:51:03; INFO; Classifiying
2023-04-05 10:51:03; INFO; Masking
2023-04-05 10:51:04; INFO; Reading MYD tile h28v14 for day 360
2023-04-05 10:51:04; INFO; Creating data/2019/h28v14/2019-360-h28v14-MYD-Simple.tif
2023-04-05 10:51:07; INFO; Generating mask
2023-04-05 10:51:07; INFO; Classifiying
2023-04-05 10:51:08; INFO; Masking
2023-04-05 10:51:08; INFO; Reading MYD tile h28v14 for day 361
2023-04-05 10:51:08; INFO; Creating data/2019/h28v14/2019-361-h28v14-MYD-Simple.tif
2023-04-05 10:51:12; INFO; Generating mask
2023-04-05 10:51:12; INFO; Classifiying
2023-04-05 10:51:12; INFO; Masking
2023-04-05 10:51:13; INFO; Reading MYD tile h28v14 for day 362
2023-04-05 10:51:13; INFO; Creating data/2019/h28v14/2019-362-h28v14-MYD-Simple.tif
2023-04-05 10:51:16; INFO; Generating mask
2023-04-05 10:51:16; INFO; Classifiying
2023-04-05 10:51:17; INFO; Masking
2023-04-05 10:51:17; INFO; Reading MYD tile h28v14 for day 363
2023-04-05 10:51:17; INFO; Creating data/2019/h28v14/2019-363-h28v14-MYD-Simple.tif
2023-04-05 10:51:20; INFO; Generating mask
2023-04-05 10:51:21; INFO; Classifiying
2023-04-05 10:51:21; INFO; Masking
2023-04-05 10:51:22; INFO; Reading MYD tile h28v14 for day 364
2023-04-05 10:51:22; INFO; Creating data/2019/h28v14/2019-364-h28v14-MYD-Simple.tif
2023-04-05 10:51:25; INFO; Generating mask
2023-04-05 10:51:25; INFO; Classifiying
2023-04-05 10:51:26; INFO; Masking
2023-04-05 10:51:26; INFO; Reading MYD tile h28v14 for day 365
2023-04-05 10:51:26; INFO; Creating data/2019/h28v14/2019-365-h28v14-MYD-Simple.tif
2023-04-05 10:51:30; INFO; Generating mask
2023-04-05 10:51:30; INFO; Classifiying
2023-04-05 10:51:31; INFO; Masking
2023-04-05 10:51:31; INFO; Reading MYD tile h28v14 for day 366
2023-04-05 10:51:31; INFO; Creating data/2019/h28v14/2019-366-h28v14-MYD-Simple.tif
2023-04-05 10:51:31; INFO; No matching HDFs found.
2023-04-05 10:51:31; INFO; Creating annual map.
2023-04-05 10:51:31; INFO; Found exclusion days for h28v14: 129 - 304
2023-04-05 10:52:12; INFO; Excluding day 129
2023-04-05 10:52:12; INFO; Excluding day 130
2023-04-05 10:52:12; INFO; Excluding day 131
...
2023-04-05 10:53:21; INFO; Excluding day 293
2023-04-05 10:53:21; INFO; Excluding day 294
2023-04-05 10:53:21; INFO; Excluding day 295
2023-04-05 10:53:21; INFO; Excluding day 296
2023-04-05 10:53:21; INFO; Excluding day 297
2023-04-05 10:53:21; INFO; Excluding day 298
2023-04-05 10:53:21; INFO; Excluding day 299
2023-04-05 10:53:21; INFO; Excluding day 300
2023-04-05 10:53:21; INFO; Excluding day 301
2023-04-05 10:53:21; INFO; Excluding day 302
2023-04-05 10:53:21; INFO; Excluding day 303
2023-04-05 10:53:21; INFO; Excluding day 304
2023-04-05 10:53:40; WARNING; Day image does not exist: data/2019/h28v14/2019-366-h28v14-MYD-Simple.tif
2023-04-05 10:53:42; INFO; Creating annual burn scar map.
2023-04-05 10:53:42; INFO; Wrote annual burn scar map to: data/2019/h28v14/MYD.A2019.h28v14.Simple.AnnualBurnScar.20230951053.tif
2023-04-05 10:53:42; INFO; Post processing.
2023-04-05 10:53:44; INFO; Wrote annual QA products to: data/2019/h28v14/MYD44W.A2019.h28v14.Simple.AnnualWaterProduct.20230951053.bin
2023-04-05 10:53:44; INFO; Wrote annual QA products to: data/2019/h28v14/MYD44W.A2019.h28v14.Simple.AnnualWaterProductQA.20230951053.bin
2023-04-05 10:53:49; INFO; Wrote annual seven class to: data/2019/h28v14/MYD44W.A2019.h28v14.Simple.AnnualSevenClass.20230951053.bin
/panfs/ccds02/nobackup/people/cssprad1/projects/modis_water/code/ancillary_masks/modis_water_src_change/combine_qa_layers/modis_water/model/Classifier.py:121: RuntimeWarning: divide by zero encountered in divide
  (((sr2 - sr1) / (sr2 + sr1)) * 10000).astype(np.int16)
/panfs/ccds02/nobackup/people/cssprad1/projects/modis_water/code/ancillary_masks/modis_water_src_change/combine_qa_layers/modis_water/model/Classifier.py:121: RuntimeWarning: invalid value encountered in divide
  (((sr2 - sr1) / (sr2 + sr1)) * 10000).astype(np.int16)
/panfs/ccds02/nobackup/people/cssprad1/projects/modis_water/code/ancillary_masks/modis_water_src_change/combine_qa_layers/modis_water/model/AnnualMap.py:74: RuntimeWarning: invalid value encountered in divide
  (sumWater / (sumWater + sumLand) * 100).astype(np.int16),
/home/cssprad1/.local/lib/python3.8/site-packages/rasterio/__init__.py:220: NotGeoreferencedWarning: Dataset has no geotransform, gcps, or rpcs. The identity matrix be returned.
  s = DatasetReader(path, driver=driver, sharing=sharing, **kwargs)
```

</div>
