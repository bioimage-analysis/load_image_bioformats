import jpype
import os
from warnings import warn
import numpy as np

'''
This module is a copy of the bioformat.py of the pims module (http://soft-matter.github.io/pims/v0.3.3/)
with some slight modifications to fit the need of the facility
'''

def _gen_jar_locations():
    """
    Generator that yields optional locations of loci_tools.jar.
    The precedence order is (highest priority first):
    1. pims package location
    2. PROGRAMDATA/pims/loci_tools.jar
    3. LOCALAPPDATA/pims/loci_tools.jar
    4. APPDATA/pims/loci_tools.jar
    5. /etc/loci_tools.jar
    6. ~/.config/pims/loci_tools.jar
    """
    yield os.path.dirname("/Users/Espenel/Desktop/1.czi")
    if 'PROGRAMDATA' in os.environ:
        yield os.path.join(os.environ['PROGRAMDATA'], 'pims')
    if 'LOCALAPPDATA' in os.environ:
        yield os.path.join(os.environ['LOCALAPPDATA'], 'pims')
    if 'APPDATA' in os.environ:
        yield os.path.join(os.environ['APPDATA'], 'pims')
    yield '/etc'
    yield os.path.join(os.path.expanduser('~'), '.config', 'pims')

def _find_jar(url=None):
    """
    Finds the location of loci_tools.jar, if necessary download it to a
    writeable location.
    """
    for loc in _gen_jar_locations():
        if os.path.isfile(os.path.join(loc, 'loci_tools.jar')):
            return os.path.join(loc, 'loci_tools.jar')

    warn('loci_tools.jar not found, downloading')
    for loc in _gen_jar_locations():
        # check if dir exists and has write access:
        if os.path.exists(loc) and os.access(loc, os.W_OK):
            break
        # if directory is pims and it does not exist, so make it (if allowed)
        if os.path.basename(loc) == 'pims' and \
           os.access(os.path.dirname(loc), os.W_OK):
            os.mkdir(loc)
            break
    else:
        raise IOError('No writeable location found. In order to use the '
                      'Bioformats reader, please download '
                      'loci_tools.jar to the pims program folder or one of '
                      'the locations provided by _gen_jar_locations().')

    from six.moves.urllib.request import urlretrieve
    if url is None:
        url = ('http://downloads.openmicroscopy.org/bio-formats/5.1.7/' +
               'artifacts/loci_tools.jar')
    urlretrieve(url, os.path.join(loc, 'loci_tools.jar'))

    return os.path.join(loc, 'loci_tools.jar')



def _maybe_tostring(field):
    if hasattr(field, 'toString'):
        return field.toString()
    else:
        return field

class MetadataRetrieve(object):
    """This class is an interface to loci.formats.meta.MetadataRetrieve. At
    initialization, it tests all the MetadataRetrieve functions and it only
    binds the ones that do not raise a java exception.
    Parameters
    ----------
    jmd: jpype._jclass.loci.formats.ome.OMEXMLMetadataImpl
        java MetadataStore, instanciated with:
            jmd = loci.formats.MetadataTools.createOMEXMLMetadata()
        and coupled to reader with `rdr.setMetadataStore(metadata)`
    Methods
    ----------
    <loci.formats.meta.MetadataRetrieve.function>(*args) : float or int or str
        see loci.formats.meta.MetadataRetrieve API on openmicroscopy.org
    """
    def __init__(self, md):
        def wrap_md(fn, name=None, paramcount=None, *args):
            if len(args) != paramcount:
                # raise sensible error for wrong number of arguments
                raise TypeError(('{0}() takes exactly {1} arguments ({2} ' +
                                 'given)').format(name, paramcount, len(args)))
            field = fn(*args)

            # deal with fields wrapped in a custom metadata type
            if hasattr(field, 'value'):
                field = field.value
            try:  # some fields have to be called
                field = field()
            except TypeError:
                pass

            # check if it is already casted to a python type by jpype
            if not hasattr(field, 'toString'):
                return field
            else:
                field = field.toString()

            # convert to int or float if possible
            try:
                return int(field)
            except ValueError:
                try:
                    return float(field)
                except ValueError:
                    return field

        self.fields = []

        for name in dir(md):
            if (name[:3] != 'get') or (name in ['getRoot', 'getClass']):
                continue
            fn = getattr(md, name)
            for paramcount in range(5):
                try:
                    field = fn(*((0,) * paramcount))
                    if field is None:
                        continue
                    # If there is no exception, wrap the function and bind.
                    def fnw(fn1=fn, naame=name, paramcount=paramcount):
                        return (lambda *args: wrap_md(fn1, naame,
                                                      paramcount, *args))
                    fnw = fnw()
                    fnw.__doc__ = ('loci.formats.meta.MetadataRetrieve.' +
                                   name + ' wrapped\nby JPype and an '
                                   'additional automatic typeconversion.\n\n')
                    setattr(self, name[3:], fnw)
                    self.fields.append(name[3:])
                    continue
                except:
                    # function is not supported by this specific reader
                    pass

    def __repr__(self):
        return '<MetadataRetrieve> Available loci.formats.meta.' + \
                'MetadataRetrieve functions: ' + ', '.join(self.fields)


class BioformatsReader(object):
    """Taken form pims/bioformats.py

    """

    def __init__(self, filename, meta=True, java_memory='512m',
                 read_mode='auto', series=0):

        super(BioformatsReader, self).__init__()

        if read_mode not in ['auto', 'jpype', 'stringbuffer', 'javacasting']:
            raise ValueError('Invalid read_mode value.')

        # Make sure that file exists before starting java
        if not os.path.isfile(filename):
            raise IOError('The file "{}" does not exist.'.format(filename))

        # Start java VM and initialize logger (globally)
        if not jpype.isJVMStarted():
            loci_path = _find_jar()
            jpype.startJVM(jpype.getDefaultJVMPath(), '-ea',
                           '-Djava.class.path=' + loci_path,
                           '-Xmx' + java_memory)
            log4j = jpype.JPackage('org.apache.log4j')
            log4j.BasicConfigurator.configure()
            log4j_logger = log4j.Logger.getRootLogger()
            log4j_logger.setLevel(log4j.Level.ERROR)

        if not jpype.isThreadAttachedToJVM():
            jpype.attachThreadToJVM()

        loci = jpype.JPackage('loci')

        # Initialize reader and metadata
        self.filename = str(filename)
        self.rdr = loci.formats.ChannelSeparator(loci.formats.ChannelFiller())
        if meta:
            self._metadata = loci.formats.MetadataTools.createOMEXMLMetadata()
            self.rdr.setMetadataStore(self._metadata)
        self.rdr.setId(self.filename)
        if meta:
            self.metadata = MetadataRetrieve(self._metadata)

        # Checkout reader dtype and define read mode
        isLittleEndian = self.rdr.isLittleEndian()
        LE_prefix = ['>', '<'][isLittleEndian]
        FormatTools = loci.formats.FormatTools
        self._dtype_dict = {FormatTools.INT8: 'i1',
                            FormatTools.UINT8: 'u1',
                            FormatTools.INT16: LE_prefix + 'i2',
                            FormatTools.UINT16: LE_prefix + 'u2',
                            FormatTools.INT32: LE_prefix + 'i4',
                            FormatTools.UINT32: LE_prefix + 'u4',
                            FormatTools.FLOAT: LE_prefix + 'f4',
                            FormatTools.DOUBLE: LE_prefix + 'f8'}
        self._dtype_dict_java = {}
        for loci_format in self._dtype_dict.keys():
            self._dtype_dict_java[loci_format] = \
                (FormatTools.getBytesPerPixel(loci_format),
                 FormatTools.isFloatingPoint(loci_format),
                 isLittleEndian)

        # Set the correct series and initialize the sizes
        self.size_series = self.rdr.getSeriesCount()
        if series >= self.size_series or series < 0:
            self.rdr.close()
            raise IndexError('Series index out of bounds.')
        self._series = series
        self._change_series()

        # Set read mode. When auto, tryout fast and check the image size.
        if read_mode == 'auto':
            Jarr = self.rdr.openBytes(0)
            if isinstance(Jarr[:], np.ndarray):
                read_mode = 'jpype'
            else:
                warn('Due to an issue with JPype 0.6.0, reading is slower. '
                     'Please consider upgrading JPype to 0.6.1 or later.')
                try:
                    im = self._jbytearr_stringbuffer(Jarr)
                    im.reshape(self._sizeRGB, self._sizeX, self._sizeY)
                except (AttributeError, ValueError):
                    read_mode = 'javacasting'
                else:
                    read_mode = 'stringbuffer'
        self.read_mode = read_mode

        # Define the names of the standard per frame metadata.
        self.frame_metadata = {}
        if meta:
            if hasattr(self.metadata, 'PlaneDeltaT'):
                self.frame_metadata['t_s'] = 'PlaneDeltaT'
            if hasattr(self.metadata, 'PlanePositionX'):
                self.frame_metadata['x_um'] = 'PlanePositionX'
            if hasattr(self.metadata, 'PlanePositionY'):
                self.frame_metadata['y_um'] = 'PlanePositionY'
            if hasattr(self.metadata, 'PlanePositionZ'):
                self.frame_metadata['z_um'] = 'PlanePositionZ'

    def _change_series(self):
        """Changes series and rereads axes, sizes and metadata.
        """
        series = self._series

        self.rdr.setSeries(series)
        sizeX = self.rdr.getSizeX()
        sizeY = self.rdr.getSizeY()
        sizeT = self.rdr.getSizeT()
        sizeZ = self.rdr.getSizeZ()
        self.isRGB = self.rdr.isRGB()
        self.isInterleaved = self.rdr.isInterleaved()
        if self.isRGB:
            sizeC = self.rdr.getRGBChannelCount()
            if self.isInterleaved:
                self._frame_shape_2D = (sizeY, sizeX, sizeC)
                self._register_get_frame(self.get_frame_2D, 'yxc')
            else:
                self._frame_shape_2D = (sizeC, sizeY, sizeX)
                self._register_get_frame(self.get_frame_2D, 'cyx')
        else:
            sizeC = self.rdr.getSizeC()
            self._frame_shape_2D = (sizeY, sizeX)


        # determine pixel type
        pixel_type = self.rdr.getPixelType()
        dtype = self._dtype_dict[pixel_type]
        java_dtype = self._dtype_dict_java[pixel_type]

        self._jbytearr_stringbuffer = \
            lambda arr: _jbytearr_stringbuffer(arr, dtype)
        self._jbytearr_javacasting = \
            lambda arr: _jbytearr_javacasting(arr, dtype, *java_dtype)
        self._pixel_type = dtype

        # get some metadata fields

        try:
            self.calibration = self.metadata.PixelsPhysicalSizeX(series)
        except AttributeError:
            try:
                self.calibration = self.metadata.PixelsPhysicalSizeY(series)
            except:
                self.calibration = None
        try:
            self.calibrationZ = self.metadata.PixelsPhysicalSizeZ(series)
        except AttributeError:
            self.calibrationZ = None

    def close(self):
        self.rdr.close()

    def get_dimension(self):
        y = self.rdr.getSizeY()
        x = self.rdr.getSizeX()
        c = self.rdr.getSizeC()
        t = self.rdr.getSizeT()
        z = self.rdr.getSizeZ()

        return {'x': x, 'y': y, 't': t, 'c': c, 'z': z}

    def get_stack(self, **coords):
        y = self.rdr.getSizeY()
        x = self.rdr.getSizeX()
        c = self.rdr.getSizeC()
        t = self.rdr.getSizeT()
        z = self.rdr.getSizeZ()
        _coords = {'t': t-1, 'c': c-1, 'z': z-1}

        _coords = {'t': 0, 'c': 0, 'z': 0}

        img = np.empty([t,z,y,x,c], np.uint16)

        for l in range(c):
            for m in range(t):
                for n in range(z):
                    _coords['c'] = l
                    _coords['t'] = m
                    _coords['z'] = n
                    j = self.rdr.getIndex(int(_coords['z']), int(_coords['c']),
                                      int(_coords['t']))

                    im_buf = np.frombuffer(self.rdr.openBytes(j)[:],
                                       dtype=self._pixel_type)
                    im_buf.shape = self._frame_shape_2D
                    im_buf = im_buf.astype(self._pixel_type, copy=False)

                    img[m,n,:,:,l] = im_buf



        return np.squeeze(img)


    def get_frame_2D(self, **coords):
        """Actual reader, returns image as 2D numpy array and metadata as
        dict.
        """

        _coords = {'t': 0, 'c': 0, 'z': 0}
        _coords.update(coords)

        if self.isRGB:
            _coords['c'] = 0
        j = self.rdr.getIndex(int(_coords['z']), int(_coords['c']),
                              int(_coords['t']))
        if self.read_mode == 'jpype':
            im = np.frombuffer(self.rdr.openBytes(j)[:],
                               dtype=self._pixel_type)

        elif self.read_mode == 'stringbuffer':
            im = self._jbytearr_stringbuffer(self.rdr.openBytes(j))
        elif self.read_mode == 'javacasting':
            im = self._jbytearr_javacasting(self.rdr.openBytes(j))

        im.shape = self._frame_shape_2D
        im = im.astype(self._pixel_type, copy=False)

        metadata = {'frame': j,
                    'series': self._series}

        if self.calibration is not None:
            metadata['pixel_size'] = self.calibration
        if self.calibrationZ is not None:
            metadata['Z_step_size'] = self.calibrationZ
        metadata.update(coords)
        for key, method in self.frame_metadata.items():
            metadata[key] = getattr(self.metadata, method)(self._series, j)

        return metadata, im



    def get_metadata_raw(self, form='dict'):
        hashtable = self.rdr.getGlobalMetadata()
        keys = hashtable.keys()
        if form == 'dict':
            result = {}
            while keys.hasMoreElements():
                key = keys.nextElement()
                result[key] = _maybe_tostring(hashtable.get(key))
        elif form == 'list':
            result = []
            while keys.hasMoreElements():
                key = keys.nextElement()
                result.append(key + ': ' + _maybe_tostring(hashtable.get(key)))
        elif form == 'string':
            result = u''
            while keys.hasMoreElements():
                key = keys.nextElement()
                result += key + ': ' + _maybe_tostring(hashtable.get(key)) + '\n'
        return result
