# coding: utf-8
# /*##########################################################################
#
# Copyright (c) 2016 European Synchrotron Radiation Facility
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
# ###########################################################################*/
"""Set of widgets to associate with a :class:'PlotWidget'.
"""

from __future__ import division

__authors__ = ["V.A. Sole", "T. Vincent"]
__license__ = "MIT"
__date__ = "28/04/2016"


import logging
import numbers
import traceback
import weakref

import numpy

from .. import icons
from .. import qt
from ...image.bilinear import BilinearImage

_logger = logging.getLogger(__name__)
_logger.setLevel(logging.DEBUG)


# PositionInfo ################################################################

class PositionInfo(qt.QWidget):
    """QWidget displaying coords converted from data coords of the mouse.

    Provide this widget with a list of couple:

    - A name to display before the data
    - A function that takes (x, y) as arguments and returns something that
      gets converted to a string.
      If the result is a float it is converted with '%.7g' format.

    To run the following sample code, a QApplication must be initialized.
    First, create a PlotWindow and add a QToolBar where to place the
    PositionInfo widget.

    >>> from silx.gui.plot import PlotWindow
    >>> from silx.gui import qt

    >>> plot = PlotWindow()  # Create a PlotWindow to add the widget to
    >>> toolBar = qt.QToolBar()  # Create a toolbar to place the widget in
    >>> plot.addToolBar(qt.Qt.BottomToolBarArea, toolBar)  # Add it to plot

    Then, create the PositionInfo widget and add it to the toolbar.
    The PositionInfo widget is created with a list of converters, here
    to display polar coordinates of the mouse position.

    >>> import math
    >>> from silx.gui.plot.PlotTools import PositionInfo

    >>> position = PositionInfo(plot, converters=[
    ...     ('Radius', lambda x, y: math.sqrt(x*x + y*y)),
    ...     ('Angle', lambda x, y: math.degrees(math.atan2(y, x)))])

    >>> toolBar.addWidget(position)  # Add the widget to the toolbar
    <...>

    >>> plot.show()  # To display the PlotWindow with the position widget

    :param plot: The PlotWidget this widget is displaying data coords from.
    :param converters: List of name to display and conversion function from
                       (x, y) in data coords to displayed value.
                       If None, the default, it displays X and Y.
    :type converters: Iterable of 2-tuple (str, function)
    :param parent: Parent widget
    """

    def __init__(self, plot, converters=None, parent=None):
        self._plotRef = weakref.ref(plot)

        super(PositionInfo, self).__init__(parent)

        if converters is None:
            converters = (('X', lambda x, y: x), ('Y', lambda x, y: y))

        self.autoSnapToActiveCurve = False
        """Toggle snapping use position to active curve.

        - True to snap used coordinates to the active curve if the active curve
        is displayed with symbols and mouse is close enough.
        If the mouse is not close to a point of the curve, values are
        displayed in red.
        - False (the default) to always use mouse coordinates.
        """

        self._fields = []  # To store (QLineEdit, name, function (x, y)->v)

        # Create a new layout with new widgets
        layout = qt.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        # layout.setSpacing(0)

        # Create all LineEdit and store them with the corresponding converter
        for name, func in converters:
            layout.addWidget(qt.QLabel('<b>' + name + ':</b>'))

            lineEdit = qt.QLineEdit()
            lineEdit.setText('------')
            lineEdit.setReadOnly(1)
            lineEdit.setFixedWidth(
                lineEdit.fontMetrics().width('##############'))
            layout.addWidget(lineEdit)
            self._fields.append((lineEdit, name, func))

        layout.addStretch(1)
        self.setLayout(layout)

        # Connect to Plot events
        plot.sigPlotSignal.connect(self._plotEvent)

    @property
    def plot(self):
        """The :class:`.PlotWindow` this widget is attached to."""
        return self._plotRef()

    def getConverters(self):
        """Return the list of converters as 2-tuple (name, function)."""
        return [(name, func) for lineEdit, name, func in self._fields]

    def _plotEvent(self, event):
        """Handle events from the Plot.

        :param dict event: Plot event
        """
        if event['event'] == 'mouseMoved':
            x, y = event['x'], event['y']  # Position in data
            styleSheet = "color: rgb(0, 0, 0);"  # Default style

            if self.autoSnapToActiveCurve and self.plot.getGraphCursor():
                # Check if near active curve with symbols.

                styleSheet = "color: rgb(255, 0, 0);"  # Style far from curve

                activeCurve = self.plot.getActiveCurve()
                if activeCurve:
                    xData, yData, legend, info, params = activeCurve[0:5]
                    if params['symbol']:  # Only handled if symbols on curve
                        closestIndex = numpy.argmin(
                            pow(xData - x, 2) + pow(yData - y, 2))

                        xClosest = xData[closestIndex]
                        yClosest = yData[closestIndex]

                        closestInPixels = self.plot.dataToPixel(
                            xClosest, yClosest, axis=params['yaxis'])
                        if closestInPixels is not None:
                            xClosest, yClosest = closestInPixels
                            xPixel, yPixel = event['xpixel'], event['ypixel']

                            if (abs(xClosest - xPixel) < 5 and
                                    abs(yClosest - yPixel) < 5):
                                # Update lineEdit style sheet
                                styleSheet = "color: rgb(0, 0, 0);"

                                # if close enough, wrap to data point coords
                                x, y = xClosest, yClosest

            for lineEdit, name, func in self._fields:
                lineEdit.setStyleSheet(styleSheet)

                try:
                    value = func(x, y)
                except:
                    lineEdit.setText('Error')
                    _logger.error(
                        "Error while converting coordinates (%f, %f)"
                        "with converter '%s'" % (x, y, name))
                    _logger.error(traceback.format_exc())
                else:
                    if isinstance(value, numbers.Real):
                        value = '%.7g' % value  # Use this for floats and int
                    else:
                        value = str(value)  # Fallback for other types
                    lineEdit.setText(value)


# ProfileToolBar ##############################################################

class ProfileToolBar(qt.QToolBar):
    """QToolBar providing profile tools operating on a :class:`PlotWindow`.

    Attributes:

    - plotWindow: Associated :class:`PlotWindow`.
    - profileWindow: Associated :class:`PlotWindow` displaying the profile.
    - actionGroup: :class:`QActionGroup` of available actions.

    :param plotWindow: :class:`PlotWindow` instance on which to operate.
    :param profileWindow: :class:`ProfileScanWidget` instance where to
                          display the profile curve or None to create one.
    :param str title: See :class:`QToolBar`.
    :param parent: See :class:`QToolBar`.
    """
    # TODO when available, listen to active image change to refresh profile
    # TODO Make it a QActionGroup instead of a QToolBar

    _POLYGON_LEGEND = '__ProfileToolBar_ROI_Polygon'

    def __init__(self, plotWindow, profileWindow=None,
                 title='Profile Selection', parent=None):
        super(ProfileToolBar, self).__init__(title, parent)
        assert plotWindow is not None
        self.plotWindow = plotWindow

        self._overlayColor = 'red'

        self._roiInfo = None  # Store start and end points and type of ROI

        if profileWindow is None:
            # Import here to avoid cyclic import
            from .PlotWindow import PlotWindow
            self.profileWindow = PlotWindow()
        else:
            self.profileWindow = profileWindow

        # Actions
        self.browseAction = qt.QAction(
            icons.getQIcon('normal'),
            'Browsing Mode', None)
        self.browseAction.setToolTip(
            'Enables zooming interaction mode')
        self.browseAction.setCheckable(True)
        self.browseAction.toggled[bool].connect(self._browseActionToggled)

        self.hLineAction = qt.QAction(
            icons.getQIcon('shape-horizontal'),
            'Horizontal Profile Mode', None)
        self.hLineAction.setToolTip(
            'Enables horizontal profile selection mode')
        self.hLineAction.setCheckable(True)
        self.hLineAction.toggled[bool].connect(self._hLineActionToggled)

        self.vLineAction = qt.QAction(
            icons.getQIcon('shape-vertical'),
            'Vertical Profile Mode', None)
        self.vLineAction.setToolTip(
            'Enables vertical profile selection mode')
        self.vLineAction.setCheckable(True)
        self.vLineAction.toggled[bool].connect(self._vLineActionToggled)

        self.lineAction = qt.QAction(
            icons.getQIcon('shape-diagonal'),
            'Fee Line Profile Mode', None)
        self.lineAction.setToolTip(
            'Enables line profile selection mode')
        self.lineAction.setCheckable(True)
        self.lineAction.toggled[bool].connect(self._lineActionToggled)

        self.clearAction = qt.QAction(
            icons.getQIcon('image'),
            'Clear Profile', None)
        self.clearAction.setToolTip(
            'Clear the profile Region of interest')
        self.clearAction.setCheckable(False)
        self.clearAction.triggered.connect(self.clearProfile)

        # ActionGroup
        self.actionGroup = qt.QActionGroup(self)
        self.actionGroup.addAction(self.browseAction)
        self.actionGroup.addAction(self.hLineAction)
        self.actionGroup.addAction(self.vLineAction)
        self.actionGroup.addAction(self.lineAction)

        self.browseAction.setChecked(True)

        # Add actions to ToolBar
        self.addAction(self.browseAction)
        self.addAction(self.hLineAction)
        self.addAction(self.vLineAction)
        self.addAction(self.lineAction)
        self.addAction(self.clearAction)

        # Add width spin box to toolbar
        self.addWidget(qt.QLabel('W:'))
        self.lineWidthSpinBox = qt.QSpinBox(self)
        self.lineWidthSpinBox.setRange(0, 1000)
        self.lineWidthSpinBox.setValue(1)
        self.lineWidthSpinBox.valueChanged[int].connect(
            self._lineWidthSpinBoxValueChangedSlot)
        self.addWidget(self.lineWidthSpinBox)

    def _lineWidthSpinBoxValueChangedSlot(self, value):
        """Listen to ROI width widget to refresh ROI and profile"""
        self.updateProfile()

    def _hLineActionToggled(self, checked):
        """Handle horizontal line profile action toggle"""
        if checked:
            self.plotWindow.setInteractiveMode('draw', shape='hline',
                                               color=None)
            self.plotWindow.sigPlotSignal.connect(self._plotWindowSlot)
        else:
            self.plotWindow.sigPlotSignal.disconnect(self._plotWindowSlot)
            # self.plotWindow.setInteractiveMode('zoom')

    def _vLineActionToggled(self, checked):
        """Handle vertical line profile action toggle"""
        if checked:
            self.plotWindow.setInteractiveMode('draw', shape='vline',
                                               color=None)
            self.plotWindow.sigPlotSignal.connect(self._plotWindowSlot)
        else:
            self.plotWindow.sigPlotSignal.disconnect(self._plotWindowSlot)
            # self.plotWindow.setInteractiveMode('zoom')

    def _lineActionToggled(self, checked):
        """Handle line profile action toggle"""
        if checked:
            self.plotWindow.setInteractiveMode('draw', shape='line',
                                               color=None)
            self.plotWindow.sigPlotSignal.connect(self._plotWindowSlot)
        else:
            self.plotWindow.sigPlotSignal.disconnect(self._plotWindowSlot)
            # self.plotWindow.setInteractiveMode('zoom')

    def _browseActionToggled(self, checked):
        """Handle browse action mode triggering"""
        if checked:
            self.plotWindow.setInteractiveMode('zoom')
        # else:
        #    self.plotWindow.setInteractiveMode('select')

    def _plotWindowSlot(self, event):
        """Listen to Plot to handle drawing events to refresh ROI and profile.
        """
        if event['event'] not in ('drawingProgress', 'drawingFinished'):
            return

        checkedAction = self.actionGroup.checkedAction()
        if checkedAction == self.hLineAction:
            lineProjectionMode = 'X'
        elif checkedAction == self.vLineAction:
            lineProjectionMode = 'Y'
        elif checkedAction == self.lineAction:
            lineProjectionMode = 'D'
        else:
            return

        roiStart, roiEnd = event['points'][0], event['points'][1]

        self._roiInfo = roiStart, roiEnd, lineProjectionMode
        self.updateProfile()

    @property
    def overlayColor(self):
        """The color to use for the ROI."""
        return self._overlayColor

    @overlayColor.setter
    def overlayColor(self, color):
        self._overlayColor = color
        self.updateProfile()

    def clearProfile(self):
        """Remove profile curve and profile area."""
        self._roiInfo = None
        self.updateProfile()

    @staticmethod
    def _alignedFullProfile(image, origin, scale, position, roiWidth, axis):
        """Get a profile along one axis on the active image

        :param numpy.ndarray image: 2D image
        :param origin: Origin of image in plot (ox, oy)
        :param scale: Scale of image in plot (sx, sy)
        :param float position: Position of profile line in plot coords
                               on the axis orthogonal to the profile direction.
        :param int roiWidth: Width of the profile in image pixels.
        :param int axis: 0 for horizontal profile, 1 for vertical.
        :return: profile curve + effective ROI area corners in plot coords
        """
        assert axis in (0, 1)

        # Convert from plot to image coords
        imgPos = int((position - origin[1 - axis]) / scale[1 - axis])

        if axis == 1:  # Vertical profile
            # Transpose image to always do a horizontal profile
            image = numpy.transpose(image)

        height, width = image.shape

        roiWidth = min(height, roiWidth)  # Clip roi width to image size

        # Get [start, end[ coords of the roi in the data
        start = int(int(imgPos) + 0.5 - roiWidth / 2.)
        start = min(max(0, start), height - roiWidth)
        end = start + roiWidth

        if start < height and end > 0:
            profile = image[max(0, start):min(end, height), :].mean(
                axis=0, dtype=numpy.float32)
        else:  # No ROI/image intersection
            profile = numpy.zeros((width,), dtype=numpy.float32)

        # Compute effective ROI in plot coords
        profileBounds = numpy.array((0, width, width, 0),
                                    dtype=numpy.float32) * scale[0] + origin[0]
        roiBounds = numpy.array((start, start, end, end),
                                dtype=numpy.float32) * scale[1] + origin[1]

        if axis == 0:  # Horizontal profile
            area = profileBounds, roiBounds
        else:  # vertical profile
            area = roiBounds, profileBounds

        return profile, area

    @staticmethod
    def _alignedPartialProfile(image, rowRange, colRange, axis):
        """Mean of a rectangular region (ROI) of an image along a given axis.

        Returned values and all parameters are in image coordinates.

        :param image: 2D data.
        :type image: numpy.ndarray with 2 dimensions.
        :param rowRange: [min, max[ of ROI rows (upper bound excluded).
        :type rowRange: 2-tuple of int (min, max) with min < max
        :param colRange: [min, max[ of ROI columns (upper bound excluded).
        :type colRange: 2-tuple of int (min, max) with min < max
        :param int axis: The axis along which to take the profile of the ROI.
                         0: Sum rows along columns.
                         1: Sum columns along rows.
        :return: Profile curve along the ROI as the mean of the intersection
                 of the ROI and the image.
        """
        assert axis in (0, 1)
        assert rowRange[0] < rowRange[1]
        assert colRange[0] < colRange[1]

        height, width = image.shape

        # Range aligned with the integration direction
        profileRange = colRange if axis == 0 else rowRange

        profileLength = abs(profileRange[1] - profileRange[0])

        # Subset of the image to use as intersection of ROI and image
        rowStart = min(max(0, rowRange[0]), height)
        rowEnd = min(max(0, rowRange[1]), height)
        colStart = min(max(0, colRange[0]), width)
        colEnd = min(max(0, colRange[1]), width)

        imgProfile = numpy.mean(image[rowStart:rowEnd, colStart:colEnd],
                                axis=axis, dtype=numpy.float32)

        # Profile including out of bound area
        profile = numpy.zeros(profileLength,  dtype=numpy.float32)

        # Place imgProfile in full profile
        offset = - min(0, profileRange[0])
        profile[offset:offset + len(imgProfile)] = imgProfile

        return profile

    def updateProfile(self):
        """Update the displayed profile and profile ROI.

        This uses the current active image of the plot and the current ROI.
        """

        # Clean previous profile area, and previous curve
        self.plotWindow.remove(self._POLYGON_LEGEND, kind='item')
        self.profileWindow.clear()
        self.profileWindow.setGraphTitle('')
        self.profileWindow.setGraphXLabel('X')
        self.profileWindow.setGraphYLabel('Y')

        if self._roiInfo is None:
            return

        imageData = self.plotWindow.getActiveImage()
        if imageData is None:
            return

        data, params = imageData[0], imageData[4]
        origin, scale = params['origin'], params['scale']

        roiWidth = max(1, self.lineWidthSpinBox.value())
        roiStart, roiEnd, lineProjectionMode = self._roiInfo

        if lineProjectionMode == 'X':  # Horizontal profile on the whole image
            profile, area = self._alignedFullProfile(
                data, origin, scale, roiStart[1], roiWidth, axis=0)

            yMin, yMax = min(area[1]), max(area[1]) - 1
            if roiWidth <= 1:
                profileName = 'Y = %g' % yMin
            else:
                profileName = 'Y = [%g, %g]' % (yMin, yMax)
            xLabel = 'Columns'

        elif lineProjectionMode == 'Y':  # Vertical profile on the whole image
            profile, area = self._alignedFullProfile(
                data, origin, scale, roiStart[0], roiWidth, axis=1)

            xMin, xMax = min(area[0]), max(area[0]) - 1
            if roiWidth <= 1:
                profileName = 'X = %g' % xMin
            else:
                profileName = 'X = [%g, %g]' % (xMin, xMax)
            xLabel = 'Rows'

        else:  # Free line profile

            # Convert start and end points in image coords as (row, col)
            startPt = ((roiStart[1] - origin[1]) / scale[1],
                       (roiStart[0] - origin[0]) / scale[0])
            endPt = ((roiEnd[1] - origin[1]) / scale[1],
                     (roiEnd[0] - origin[0]) / scale[0])

            if (int(startPt[0]) == int(endPt[0]) or
                    int(startPt[1]) == int(endPt[1])):
                # Profile is aligned with one of the axes

                # Convert to int
                startPt = int(startPt[0]), int(startPt[1])
                endPt = int(endPt[0]), int(endPt[1])

                # Ensure startPt <= endPt
                if startPt[0] > endPt[0] or startPt[1] > endPt[1]:
                    startPt, endPt = endPt, startPt

                if startPt[0] == endPt[0]:  # Row aligned
                    rowRange = (int(startPt[0] + 0.5 - 0.5 * roiWidth),
                                int(startPt[0] + 0.5 + 0.5 * roiWidth))
                    colRange = startPt[1], endPt[1] + 1
                    profile = self._alignedPartialProfile(
                        data, rowRange, colRange, axis=0)

                else:  # Column aligned
                    rowRange = startPt[0], endPt[0] + 1
                    colRange = (int(startPt[1] + 0.5 - 0.5 * roiWidth),
                                int(startPt[1] + 0.5 + 0.5 * roiWidth))
                    profile = self._alignedPartialProfile(
                        data, rowRange, colRange, axis=1)

                # Convert ranges to plot coords to draw ROI area
                area = (
                    numpy.array(
                        (colRange[0], colRange[1], colRange[1], colRange[0]),
                        dtype=numpy.float32) * scale[0] + origin[0],
                    numpy.array(
                        (rowRange[0], rowRange[0], rowRange[1], rowRange[1]),
                        dtype=numpy.float32) * scale[1] + origin[1])

            else:  # General case: use bilinear interpolation

                # Ensure startPt <= endPt
                if (startPt[1] > endPt[1] or (
                        startPt[1] == endPt[1] and startPt[0] > endPt[0])):
                    startPt, endPt = endPt, startPt

                bilinear = BilinearImage(data)

                # Offset start/end positions of 0.5 pixel to use pixel center
                # rather than pixel lower left corner for interpolation
                # This is only valid if image is displayed with nearest.
                profile = bilinear.profile_line(
                    (startPt[0] - 0.5, startPt[1] - 0.5),
                    (endPt[0] - 0.5, endPt[1] - 0.5),
                    roiWidth)

                # Extend ROI with half a pixel on each end, and
                # Convert back to plot coords (x, y)
                length = numpy.sqrt((endPt[0] - startPt[0]) ** 2 +
                                    (endPt[1] - startPt[1]) ** 2)
                dRow = (endPt[0] - startPt[0]) / length
                dCol = (endPt[1] - startPt[1]) / length

                # Extend ROI with half a pixel on each end
                startPt = startPt[0] - 0.5 * dRow, startPt[1] - 0.5 * dCol
                endPt = endPt[0] + 0.5 * dRow, endPt[1] + 0.5 * dCol

                # Rotate deltas by 90 degrees to apply line width
                dRow, dCol = dCol, -dRow

                area = (
                    numpy.array((startPt[1] - 0.5 * roiWidth * dCol,
                                 startPt[1] + 0.5 * roiWidth * dCol,
                                 endPt[1] + 0.5 * roiWidth * dCol,
                                 endPt[1] - 0.5 * roiWidth * dCol),
                                dtype=numpy.float32) * scale[1] + origin[1],
                    numpy.array((startPt[0] - 0.5 * roiWidth * dRow,
                                 startPt[0] + 0.5 * roiWidth * dRow,
                                 endPt[0] + 0.5 * roiWidth * dRow,
                                 endPt[0] - 0.5 * roiWidth * dRow),
                                dtype=numpy.float32) * scale[0] + origin[0])

            y0, x0 = startPt
            y1, x1 = endPt
            if x1 == x0 or y1 == y0:
                profileName = 'From (%g, %g) to (%g, %g)' % (x0, y0, x1, y1)
            else:
                m = (y1 - y0) / (x1 - x0)
                b = y0 - m * x0
                profileName = 'y = %g * x %+g ; width=%d' % (m, b, roiWidth)
            xLabel = 'Distance'

        coords = numpy.arange(len(profile), dtype=numpy.float32)
        # TODO coords in plot coords?

        self.profileWindow.setGraphTitle(profileName)
        self.profileWindow.addCurve(coords, profile,
                                    legend=profileName,
                                    xlabel=xLabel,
                                    color=self.overlayColor)

        self.plotWindow.addItem(area[0], area[1],
                                legend=self._POLYGON_LEGEND,
                                color=self.overlayColor,
                                shape='polygon', fill=True,
                                replace=False)

        self.profileWindow.show()
