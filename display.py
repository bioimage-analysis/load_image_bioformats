import numpy as np



def normalize(arr):
    """This normalizes an array to values between 0 and 1.

    Parameters
    ----------
    arr : ndarray

    Returns
    -------
    ndarray of float
        normalized array
    """
    ptp = arr.max() - arr.min()
    # Handle edge case of a flat image.
    if ptp == 0:
        ptp = 1
    scaled_arr = (arr - arr.min()) / ptp
    return scaled_arr

def _monochannel_to_rgb(image, rgb):
    """
    convert monochrome image to rgb.

    Parameters
    ----------
    image : ndarray
    rgb : list

    Returns
    -------
    image_rgb: array , shape (image).
    """
    image_rgb = normalize(image).reshape(*(image.shape + (1,)))
    image_rgb = image_rgb * np.asarray(rgb).reshape(*((1,)*image.ndim + (3,)))
    return image_rgb


def to_rgb(image, auto=True, normed=True, bf=True, **kwargs):
    """
    convert monochrome image to rgb.

    Parameters
    ----------
    image : ndarray
        Image of shape (C, M, N)
    auto : bool, optional
        If True, will automaticaly chose colors
        If False, chose between: White, Red, Green,
                                 Blue, Magenta, Orange,
                                 Cyan
    normed : bool, optional
        Convert image to type uint8
    bf : bool, optional
        If you have a brightfield image in your stack

    Returns
    -------
    image_rgb: array , shape (M, N, C).

    Examples
    --------
    img.shape
    >>> (3, 1960, 1960)
    result = display.to_rgb(img, auto = False,bf = True,
                            Channel_0 = 'Blue', Channel_1 = 'Red',
                            Channel_2 = "White")
    result.shape
    >>> (1960, 1960,3)

    """
    White = [255, 255, 255]
    Red = [255, 0, 0]
    Green = [0, 255, 0]
    Blue = [0, 0, 255]
    Magenta = [255, 0, 255]
    Orange = [255, 128, 0]
    Cyan = [0, 255, 255]

    channels = image.shape[-1]
    shape_rgb = image.shape[:-1] + (3,)

    if auto == True:

        if channels == 1:    # white
            rgbs = [[255, 255, 255]]

        elif channels == 2 and bf == False:  # green, red
            rgbs = [[0, 255, 0], [255, 0, 0]]
        elif channels == 2 and bf == True:  # green, white
            rgbs = [[0, 255, 0], [255, 255, 255]]

        elif channels == 3 and bf == False:  # blue, green, red
            rgbs = [[0, 0, 255], [0, 255, 0], [255, 0, 0]]
        elif channels == 3 and bf == True:  # blue, green, white
            rgbs = [[0, 0, 255], [0, 255, 0], [255, 255, 255]]

        elif channels == 4 and bf == False:  # cyan, green, magenta, red
            rgbs = [[0, 0, 255], [0, 255, 0], [255, 0, 0], [255, 0, 255]]
        elif channels == 4 and bf == True:  # cyan, green, magenta, white
            rgbs = [[0, 0, 255], [0, 255, 0], [255, 0, 0], [255, 255, 255]]

        elif channels == 5 and bf == True:  # cyan, green, magenta, red, white
            rgbs = [[0, 0, 255], [0, 255, 0],
                    [255, 0, 0],  [255, 0, 255],
                    [255, 255, 255]]

        else:
            raise IndexError('Not enough color values to build rgb image')
    else:
        if channels == 1:
            rgbs = [eval(kwargs['Channel_0'])]
        elif channels == 2:
            rgbs = [eval(kwargs['Channel_0']), eval(kwargs['Channel_1'])]
        elif channels == 3:
            rgbs = [eval(kwargs['Channel_0']), eval(kwargs['Channel_1']),
                    eval(kwargs['Channel_2'])]
        elif channels == 4:
            rgbs = [eval(kwargs['Channel_0']), eval(kwargs['Channel_1']),
                    eval(kwargs['Channel_2']), eval(kwargs['Channel_3'])]
        elif channels == 5:
            rgbs = [eval(kwargs['Channel_0']), eval(kwargs['Channel_1']),
                    eval(kwargs['Channel_2']), eval(kwargs['Channel_3']),
                    eval(kwargs['Channel_4'])]

    result = np.zeros(shape_rgb)
    for i in range(channels):
        result += _monochannel_to_rgb(image[...,i], rgbs[i])

    result = result.clip(0, 255)

    if normed:
        result = (normalize(result) * 255).astype('uint8')

    return result
