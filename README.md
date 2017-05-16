### (load_image_bioformats is a simplified copy of [PIMS](https://github.com/soft-matter/pims))

# How could load_image_bioformats be helpful:

In microscopy, every company has their own proprietary file format (Nikon has .nd2, Zeiss has .czi, etc.) and so you need to be able to parse and interpret the file to extract the arrays and the metadata. For that purpose, the mains available software is Bio-Formats which is developed by the Open Microscopy Environment (OME) consortium.

Using load_image_bioformats you can read and load different format into numpy array which you can then manipulate for your image analysis/processing need. It also help you extract the metadata. See [this example](https://github.com/bioimage-analysis/load_image_bioformats/blob/master/Example_usage_bioformats.ipynb) to understand how it works. 

You can also find an alternative version of the usage of bioformats with Python which doesn't necessitate to build a bridge with java on our website:

[http://bioimage-analysis.stanford.edu/guides/3-Loading_microscopy_images/](http://bioimage-analysis.stanford.edu/guides/3-Loading_microscopy_images/)
