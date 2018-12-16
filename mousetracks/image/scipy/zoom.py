# Copyright (C) 2003-2005 Peter J. Verveer
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#
# 3. The name of the author may not be used to endorse or promote
#    products derived from this software without specific prior
#    written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS
# OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE
# GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from __future__ import division, absolute_import
import numpy
import math

from . import _ni_support
try:
    from . import _nd_image
except ImportError:
    from scipy.ndimage import _nd_image


def _extend_mode_to_code(mode):
    mode = _ni_support._extend_mode_to_code(mode)
    return mode
    
    
def spline_filter1d(input, order=3, axis=-1, output=numpy.float64):
    """
    Calculates a one-dimensional spline filter along the given axis.

    The lines of the array along the given axis are filtered by a
    spline filter. The order of the spline must be >= 2 and <= 5.

    Parameters
    ----------
    input : array_like
        The input array.
    order : int, optional
        The order of the spline, default is 3.
    axis : int, optional
        The axis along which the spline filter is applied. Default is the last
        axis.
    output : ndarray or dtype, optional
        The array in which to place the output, or the dtype of the returned
        array. Default is `numpy.float64`.

    Returns
    -------
    spline_filter1d : ndarray or None
        The filtered input. If `output` is given as a parameter, None is
        returned.

    """
    if order < 0 or order > 5:
        raise RuntimeError('spline order not supported')
    input = numpy.asarray(input)
    if numpy.iscomplexobj(input):
        raise TypeError('Complex type not supported')
    output, return_value = _ni_support._get_output(output, input)
    if order in [0, 1]:
        output[...] = numpy.array(input)
    else:
        axis = _ni_support._check_axis(axis, input.ndim)
        _nd_image.spline_filter1d(input, order, axis, output)
    return return_value


def spline_filter(input, order=3, output=numpy.float64):
    """
    Multi-dimensional spline filter.

    For more details, see `spline_filter1d`.

    See Also
    --------
    spline_filter1d

    Notes
    -----
    The multi-dimensional filter is implemented as a sequence of
    one-dimensional spline filters. The intermediate arrays are stored
    in the same data type as the output. Therefore, for output types
    with a limited precision, the results may be imprecise because
    intermediate results may be stored with insufficient precision.

    """
    if order < 2 or order > 5:
        raise RuntimeError('spline order not supported')
    input = numpy.asarray(input)
    if numpy.iscomplexobj(input):
        raise TypeError('Complex type not supported')
    output, return_value = _ni_support._get_output(output, input)
    if order not in [0, 1] and input.ndim > 0:
        for axis in range(input.ndim):
            spline_filter1d(input, order, axis, output=output)
            input = output
    else:
        output[...] = input[...]
    return return_value
    
def zoom(input, zoom, output=None, order=3, mode='constant', cval=0.0,
         prefilter=True):
    """
    Zoom an array.

    The array is zoomed using spline interpolation of the requested order.

    Parameters
    ----------
    input : ndarray
        The input array.
    zoom : float or sequence, optional
        The zoom factor along the axes. If a float, `zoom` is the same for each
        axis. If a sequence, `zoom` should contain one value for each axis.
    output : ndarray or dtype, optional
        The array in which to place the output, or the dtype of the returned
        array.
    order : int, optional
        The order of the spline interpolation, default is 3.
        The order has to be in the range 0-5.
    mode : str, optional
        Points outside the boundaries of the input are filled according
        to the given mode ('constant', 'nearest', 'reflect' or 'wrap').
        Default is 'constant'.
    cval : scalar, optional
        Value used for points outside the boundaries of the input if
        ``mode='constant'``. Default is 0.0
    prefilter : bool, optional
        The parameter prefilter determines if the input is pre-filtered with
        `spline_filter` before interpolation (necessary for spline
        interpolation of order > 1).  If False, it is assumed that the input is
        already filtered. Default is True.

    Returns
    -------
    zoom : ndarray or None
        The zoomed input. If `output` is given as a parameter, None is
        returned.

    """
    if order < 0 or order > 5:
        raise RuntimeError('spline order not supported')
    input = numpy.asarray(input)
    if numpy.iscomplexobj(input):
        raise TypeError('Complex type not supported')
    if input.ndim < 1:
        raise RuntimeError('input and output rank must be > 0')
    mode = _extend_mode_to_code(mode)
    if prefilter and order > 1:
        filtered = spline_filter(input, order, output=numpy.float64)
    else:
        filtered = input
    zoom = _ni_support._normalize_sequence(zoom, input.ndim)
    output_shape = tuple(
            [int(round(ii * jj)) for ii, jj in zip(input.shape, zoom)])

    zoom_div = numpy.array(output_shape, float) - 1
    zoom = (numpy.array(input.shape) - 1) / zoom_div

    # Zooming to non-finite values is unpredictable, so just choose
    # zoom factor 1 instead
    zoom[~numpy.isfinite(zoom)] = 1

    output, return_value = _ni_support._get_output(output, input,
                                                   shape=output_shape)
    zoom = numpy.asarray(zoom, dtype=numpy.float64)
    zoom = numpy.ascontiguousarray(zoom)
    _nd_image.zoom_shift(filtered, zoom, None, output, order, mode, cval)
    return return_value
