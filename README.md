### (load_image_bioformats is a simplified copy of [PIMS](https://github.com/soft-matter/pims))

# How could load_image_bioformats be helpful:

In microscopy, every company has their own proprietary file format (Nikon has .nd2, Zeiss has .czi, etc.) and so you need to be able to parse and interpret the file to extract the arrays and the metadata. For that purpose, the mains available software is Bio-Formats which is developed by the Open Microscopy Environment (OME) consortium.

Here you can read and load different format into numpy array which you can then manipulate for your image analysis/processing need. It also help you extract the metadata. 
