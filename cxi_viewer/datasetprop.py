#from PyQt4 import QtGui, QtCore, QtOpenGL, Qt
from PySide import QtGui, QtCore, QtOpenGL
from operator import mul
import numpy,ctypes
import h5py
from matplotlib import colors
from matplotlib import cm
import pyqtgraph

def sizeof_fmt(num):
    for x in ['bytes','kB','MB','GB']:
        if num < 1024.0:
            return "%3.1f %s" % (num, x)
        num /= 1024.0
    return "%3.1f %s" % (num, 'TB')
    

# Consistent function nomenclature:
# - currDisplayProp['propertyBla'] => class variables defining current property
# - setProperty                    => stores property specified in widgets to class variables propertyBla,propertyBlabla,...
#(- refreshProperty                => refreshes widgets that have dependencies on dataset )
# - clearProperty                  => sets property to default (+ refreshes property)
#
class DatasetProp(QtGui.QWidget):
    displayPropChanged = QtCore.Signal(dict)
    def __init__(self,parent=None):
        QtGui.QWidget.__init__(self,parent)
        self.setFocusPolicy(QtCore.Qt.ClickFocus)

        self.viewer = parent
        # this dict holds all current settings
        self.currDisplayProp = {}
        self.vbox = QtGui.QVBoxLayout()
        # scrolling
        self.vboxScroll = QtGui.QVBoxLayout()
        self.scrollWidget = QtGui.QWidget()
        self.scrollWidget.setLayout(self.vboxScroll)
        self.scrollArea = QtGui.QScrollArea()
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setFrameShape(QtGui.QFrame.NoFrame)
        self.scrollArea.setWidget(self.scrollWidget)
        self.scrollArea.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.scrollArea.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.vbox.addWidget(self.scrollArea)
        # GENERAL PROPERTIES
        # properties: dataset
        self.generalBox = QtGui.QGroupBox("General Properties");
        self.generalBox.vbox = QtGui.QVBoxLayout()
        self.generalBox.setLayout(self.generalBox.vbox)
        self.dimensionality = QtGui.QLabel("Dimensions:", parent=self)
        self.datatype = QtGui.QLabel("Data Type:", parent=self)
        self.datasize = QtGui.QLabel("Data Size:", parent=self)
        self.dataform = QtGui.QLabel("Data Form:", parent=self)
        self.currentImg = QtGui.QLabel("Visible Image:", parent=self)
        self.generalBox.vbox.addWidget(self.dimensionality)
        self.generalBox.vbox.addWidget(self.datatype)
        self.generalBox.vbox.addWidget(self.datasize)
        self.generalBox.vbox.addWidget(self.dataform)
        self.generalBox.vbox.addWidget(self.currentImg)
        # properties: image stack
        self.imageStackBox = QtGui.QGroupBox("Image Stack Properties");
        self.imageStackBox.vbox = QtGui.QVBoxLayout()
        self.imageStackBox.setLayout(self.imageStackBox.vbox)
        # property: image stack plots width
        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(QtGui.QLabel("Width:"))
        self.imageStackSubplots = QtGui.QSpinBox(parent=self)
        self.imageStackSubplots.setMinimum(1)
#        self.imageStackSubplots.setMaximum(5)
        hbox.addWidget(self.imageStackSubplots)
        self.imageStackBox.vbox.addLayout(hbox)
        # properties: selected image
        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(QtGui.QLabel("Selected Image:"))
        self.imageStackImageSelected = QtGui.QLabel("None",parent=self)
        hbox.addWidget(self.imageStackImageSelected)
        self.imageStackBox.vbox.addLayout(hbox)
        # DISPLAY PROPERTIES
        self.displayBox = QtGui.QGroupBox("Display Properties");
        self.displayBox.vbox = QtGui.QVBoxLayout()

        self.intensityHistogram = pyqtgraph.PlotWidget()
        self.intensityHistogram.hideAxis('left')
        self.intensityHistogram.hideAxis('bottom')
        self.intensityHistogram.setFixedHeight(50)
        region = pyqtgraph.LinearRegionItem(values=[0,1],brush="#ffffff15")
        self.intensityHistogram.addItem(region)
        self.intensityHistogram.autoRange()
        self.intensityHistogramRegion = region

        # Make the histogram fit the available width
        self.intensityHistogram.setSizePolicy(QtGui.QSizePolicy.Ignored,QtGui.QSizePolicy.Preferred)
        self.displayBox.vbox.addWidget(self.intensityHistogram)
        # property: NORM        
        # normVmax
        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(QtGui.QLabel("Maximum value:"))
        self.displayMax = QtGui.QDoubleSpinBox(parent=self)
        self.displayMax.setMinimum(-1000000.)
        self.displayMax.setMaximum(1000000.)
        self.displayMax.setSingleStep(1.)
        hbox.addWidget(self.displayMax)
        self.displayBox.vbox.addLayout(hbox)
        # normVmin
        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(QtGui.QLabel("Minimum value:"))
        self.displayMin = QtGui.QDoubleSpinBox(parent=self)
        self.displayMin.setMinimum(-1000000.)
        self.displayMin.setMaximum(1000000.)
        self.displayMin.setSingleStep(1.)
        hbox.addWidget(self.displayMin)
        self.displayBox.vbox.addLayout(hbox)


        # normClamp
        hbox = QtGui.QHBoxLayout()
        label = QtGui.QLabel("Clamp")
        label.setToolTip("If enabled set values outside the min/max range to min/max")
        hbox.addWidget(label)
        self.displayClamp = QtGui.QCheckBox("",parent=self)
        hbox.addWidget(self.displayClamp)
        hbox.addStretch()
        self.displayColormap = QtGui.QPushButton("Colormap",parent=self)
        self.displayColormap.setFixedSize(QtCore.QSize(100,30))
        self.displayColormap.setMenu(self.viewer.colormapMenu)
        hbox.addWidget(self.displayColormap)

        self.displayBox.vbox.addLayout(hbox)
        # normText
        vbox = QtGui.QVBoxLayout()
        vbox.addWidget(QtGui.QLabel("Scaling:"))
        self.displayLin = QtGui.QRadioButton("Linear")
        self.displayLog = QtGui.QRadioButton("Logarithmic")
        self.displayPow = QtGui.QRadioButton("Power")
        vbox.addWidget(self.displayLin)
        vbox.addWidget(self.displayLog)
        # normGamma
        hbox = QtGui.QHBoxLayout()
        self.displayGamma = QtGui.QDoubleSpinBox(parent=self)
        self.displayGamma.setValue(0.25);
        self.displayGamma.setSingleStep(0.25);
        hbox.addWidget(self.displayPow)
        hbox.addWidget(self.displayGamma)        
        vbox.addLayout(hbox)
        self.displayBox.vbox.addLayout(vbox)
        self.displayBox.setLayout(self.displayBox.vbox)

        # properties: IMAGE
        self.imageBox = QtGui.QGroupBox("Image Properties");
        self.imageBox.vbox = QtGui.QVBoxLayout()
        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(QtGui.QLabel("Image Range:"))
        self.imageRange = QtGui.QLabel("None",parent=self)
        hbox.addWidget(self.imageRange)
        self.imageBox.vbox.addLayout(hbox)
        self.imageBox.setLayout(self.imageBox.vbox)

        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(QtGui.QLabel("Image Sum:"))
        self.imageSum = QtGui.QLabel("None",parent=self)
        hbox.addWidget(self.imageSum)
        self.imageBox.vbox.addLayout(hbox)

        self.imageBox.hide()

        self.filterBox = QtGui.QGroupBox("Filters");
        self.filterBox.vbox = QtGui.QVBoxLayout()
        self.filterBox.setLayout(self.filterBox.vbox)
        self.filterBox.hide()
        self.activeFilters = []
        self.inactiveFilters = []

        # add all widgets to main vbox
        self.vboxScroll.addWidget(self.generalBox)
        self.vboxScroll.addWidget(self.imageStackBox)
        self.vboxScroll.addWidget(self.imageBox)
        self.vboxScroll.addWidget(self.displayBox)
        self.vboxScroll.addWidget(self.filterBox)
        self.vboxScroll.addStretch()
        self.setLayout(self.vbox)
        # clear all properties
        self.clear()
        # connect signals
        self.imageStackSubplots.editingFinished.connect(self.emitDisplayProp)    
        self.displayMax.editingFinished.connect(self.checkLimits)
        self.displayMin.editingFinished.connect(self.checkLimits)
        self.displayClamp.stateChanged.connect(self.emitDisplayProp)
        self.displayLin.toggled.connect(self.emitDisplayProp)        
        self.displayLog.toggled.connect(self.emitDisplayProp)
        self.displayPow.toggled.connect(self.emitDisplayProp)
        self.displayGamma.editingFinished.connect(self.emitDisplayProp)
        self.viewer.colormapActionGroup.triggered.connect(self.emitDisplayProp)
    def clear(self):
        self.clearDisplayProp()
        self.clearDataset()
    def clearDisplayProp(self):
        self.clearImageStackSubplots()
        self.clearNorm()
        self.clearColormap()
    # DATASET
    def setDataset(self,dataset=None,format=2):
        self.dataset = dataset
        if dataset != None:
            self.dataset = dataset
            string = "Dimensions: "
            for d in dataset.shape:
                string += str(d)+"x"
            string = string[:-1]
            self.dimensionality.setText(string)
            self.datatype.setText("Data Type: %s" % (dataset.dtype.name))
            self.datasize.setText("Data Size: %s" % sizeof_fmt(dataset.dtype.itemsize*reduce(mul,dataset.shape)))
            if dataset.isCXIStack():
                form = "%iD Data Stack" % dataset.getCXIFormat()
            else:
                form = "%iD Data" % dataset.getCXIFormat()
            self.dataform.setText("Data form: %s" % form)
            if dataset.isCXIStack():
                self.imageStackBox.show()
            else:
                self.imageStackBox.hide()
        else:
            self.clearDataset()
    def refreshDatasetImg(self,img):
        self.currentImg.setText("Visible Image: %i" % img)
    def clearDataset(self):
        self.dataset = None
        self.dimensionality.setText("Dimensions: ")
        self.datatype.setText("Data Type: ")
        self.datasize.setText("Data Size: ")
        self.dataform.setText("Data Form: ")
        self.imageStackBox.hide()
    # VIEW
    def onImageSelected(self,selectedImage):
        self.imageStackImageSelected.setText(str(selectedImage))
        if self.dataset != None and selectedImage != None:
            self.imageRange.setText("%d to %d" %(numpy.min(self.dataset[selectedImage]),numpy.max(self.dataset[selectedImage])))
            self.imageSum.setText(str(numpy.sum(self.dataset[selectedImage])))
            self.imageBox.show()
            (hist,edges) = numpy.histogram(self.dataset[selectedImage],bins=100)
            self.intensityHistogram.clear()
            edges = (edges[:-1]+edges[1:])/2.0
            item = self.intensityHistogram.plot(edges,hist,fillLevel=0,fillBrush=QtGui.QColor(255, 255, 255, 128),antialias=True)
            self.intensityHistogram.getPlotItem().getViewBox().setMouseEnabled(x=False,y=False)
            region = pyqtgraph.LinearRegionItem(values=[self.displayMin.value(),self.displayMax.value()],brush="#ffffff15")
            region.sigRegionChangeFinished.connect(self.onHistogramClicked)
            self.intensityHistogram.addItem(region)
            self.intensityHistogram.autoRange()
            self.intensityHistogramRegion = region
        else:
            self.imageBox.hide()
    def onHistogramClicked(self,region):
        (min,max) = region.getRegion()
        self.displayMin.setValue(min)
        self.displayMax.setValue(max)
        self.emitDisplayProp()
    # NORM
    def setNorm(self):
        P = self.currDisplayProp
        P["normVmin"] = self.displayMin.value()
        P["normVmax"] = self.displayMax.value()
        P["normClamp"] = self.displayClamp.isChecked()
        if self.displayLin.isChecked():
            P["normScaling"] = "lin"
        elif self.displayLog.isChecked():
            P["normScaling"] = "log"
        else:
            P["normScaling"] = "pow"
        P["normGamma"] = self.displayGamma.value()
        self.intensityHistogramRegion.setRegion([self.displayMin.value(),self.displayMax.value()])
    def clearNorm(self):
        settings = QtCore.QSettings()


        if(settings.contains("normVmax")):
            normVmax = settings.value('normVmax')
        else:
            normVmax = 1000.
        if(settings.contains("normVmin")):
            normVmin = settings.value('normVmin')
        else:
            normVmin = 10.
        self.displayMin.setValue(normVmin)
        self.displayMax.setValue(normVmax)
        if(settings.contains("normClamp")):
            normClamp = settings.value('normClamp')
        else:
            normClamp = True
        self.displayClamp.setChecked(normClamp)
        if(settings.contains("normGamma")):
            self.displayGamma.setValue(settings.value("normGamma"))
        else:
            self.displayGamma.setValue(0.25)
        if(settings.contains("normScaling")):
            norm = settings.value("normScaling")
            if(norm == "lin"):
                self.displayLin.setChecked(True)
            elif(norm == "log"):
                self.displayLog.setChecked(True)
            elif(norm == "pow"):
                self.displayPow.setChecked(True)
            else:
                sys.exit(-1)
        else:
            self.displayLog.setChecked(True)
        self.setNorm()
    # COLORMAP
    def setColormap(self,foovalue=None):
        P = self.currDisplayProp
        a = self.viewer.colormapActionGroup.checkedAction()
        self.displayColormap.setText(a.text())        
        self.displayColormap.setIcon(a.icon())        
        P["colormapText"] = a.text()

    def clearColormap(self):
#        self.displayColormap.setCurrentIndex(0)
        self.setColormap()
    # STACK
    def setImageStackSubplots(self,foovalue=None):
        P = self.currDisplayProp
        P["imageStackSubplotsValue"] = self.imageStackSubplots.value()
    def clearImageStackSubplots(self):
        self.imageStackSubplots.setValue(1)
        self.setImageStackSubplots()
    # FILTERS
    def addFilter(self,dataset):
        if self.inactiveFilters == []:
            filterWidget = FilterWidget(self,dataset)
            filterWidget.limitsChanged.connect(self.emitDisplayProp)
            self.filterBox.vbox.addWidget(filterWidget)
            self.activeFilters.append(filterWidget)
        else:
            self.activeFilters.append(self.inactiveFilters.pop(0))
            filterWidget = self.activeFilters[-1]
            filterWidget.show()
            filterWidget.refreshDataset(dataset)
        self.setFilters()
        self.filterBox.show()
    def removeFilter(self,index):
        filterWidget = self.activeFilters.pop(index)
        self.filterBox.vbox.removeWidget(filterWidget)
        self.filterBox.vbox.addWidget(filterWidget)
        self.inactiveFilters.append(filterWidget)
        filterWidget.hide()
        filterWidget.histogram.clear()
        filterWidget.hide()
        self.setFilters()
        if self.activeFilters == []:
            self.filterBox.hide()
    def setFilters(self,fooRegion=None):
        P = self.currDisplayProp
        P["filterMask"] = []
        if self.activeFilters != []:
            for f in self.activeFilters:
                if P["filterMask"] == []:
                    P["filterMask"] = numpy.ones(len(f.dataset),dtype="bool")
                vmin = float(f.vminLineEdit.text())
                vmax= float(f.vmaxLineEdit.text())
                data = numpy.array(f.dataset,dtype="float")
                P["filterMask"] *= (data >= vmin) * (data <= vmax)
            Ntot = len(data)
            Nsel = P["filterMask"].sum()
            p = 100*Nsel/(1.*Ntot)
        else:
            Ntot = 0
            Nsel = 0
            p = 100.
        self.filterBox.setTitle("Filters (yield: %.2f%% - %i/%i)" % (p,Nsel,Ntot))
    def refreshFilter(self,dataset,index):
        self.activeFilters[index].refreshDataset(dataset)
    # update and emit current diplay properties
    def emitDisplayProp(self,foovalue=None):
        self.setImageStackSubplots()
        self.setNorm()
        self.setColormap()
        self.setFilters()
        self.displayPropChanged.emit(self.currDisplayProp)
    def checkLimits(self,foovalue=None):
        self.displayMax.setMinimum(self.displayMin.value())
        self.displayMin.setMaximum(self.displayMax.value())
        self.emitDisplayProp()
    def keyPressEvent(self,event):
        if event.key() == QtCore.Qt.Key_H:
            if self.isVisible():
                self.hide()
            else:
                self.show()


def paintColormapIcons(W,H):
    a = numpy.outer(numpy.ones(shape=(H,)),numpy.linspace(0.,1.,W))
    maps=[m for m in cm.datad if not m.endswith("_r")]
    mappable = cm.ScalarMappable()
    mappable.set_norm(colors.Normalize())
    iconDict = {}
    for m in maps:
        mappable.set_cmap(m)
        temp = mappable.to_rgba(a,None,True)[:,:,:]
        a_rgb = numpy.zeros(shape=(H,W,4),dtype=numpy.uint8)
        # For some reason we have to swap indices !? Otherwise inverted colors...
        a_rgb[:,:,2] = temp[:,:,0]
        a_rgb[:,:,1] = temp[:,:,1]
        a_rgb[:,:,0] = temp[:,:,2]
        a_rgb[:,:,3] = 0xff
        img = QtGui.QImage(a_rgb,W,H,QtGui.QImage.Format_ARGB32)
        icon = QtGui.QIcon(QtGui.QPixmap.fromImage(img))
        iconDict[m] = icon
    return iconDict


class FilterWidget(QtGui.QWidget):
    limitsChanged = QtCore.Signal(float,float)
    def __init__(self,parent,dataset):
        QtGui.QWidget.__init__(self,parent)
        vbox = QtGui.QVBoxLayout()
        nameLabel = QtGui.QLabel(dataset.name)
        yieldLabel = QtGui.QLabel("")
        vmin = numpy.min(dataset)
        vmax = numpy.max(dataset)
        histogram = pyqtgraph.PlotWidget(self)
        histogram.hideAxis('left')
        histogram.hideAxis('bottom')
        histogram.setFixedHeight(50)
        # Make the histogram fit the available width
        histogram.setSizePolicy(QtGui.QSizePolicy.Ignored,QtGui.QSizePolicy.Preferred)
        region = pyqtgraph.LinearRegionItem(values=[vmin,vmax],brush="#ffffff15")
        region.sigRegionChangeFinished.connect(self.syncLimits)
        histogram.addItem(region)
        histogram.autoRange()
        vbox.addWidget(histogram)
        vbox.addWidget(nameLabel)
        vbox.addWidget(yieldLabel)
        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(QtGui.QLabel("Min.:"))
        hbox.addWidget(QtGui.QLabel("Max.:"))
        vbox.addLayout(hbox)
        hbox = QtGui.QHBoxLayout()
        vminLineEdit = QtGui.QLineEdit(self)
        vminLineEdit.setText("%.3e" % vmin)
        validator = QtGui.QDoubleValidator()
        validator.setDecimals(3)
        validator.setNotation(QtGui.QDoubleValidator.ScientificNotation)
        vminLineEdit.setValidator(validator)
        hbox.addWidget(vminLineEdit)
        vmaxLineEdit = QtGui.QLineEdit(self)
        vmaxLineEdit.setText("%.3e" % vmax)
        validator = QtGui.QDoubleValidator()
        validator.setNotation(QtGui.QDoubleValidator.ScientificNotation)
        vmaxLineEdit.setValidator(validator)
        hbox.addWidget(vmaxLineEdit)
        vbox.addLayout(hbox)
        self.setLayout(vbox)
        self.dataset = dataset
        self.histogram = histogram
        self.histogram.region = region
        self.histogram.itemPlot = None
        #self.datasetBox = datasetBox
        self.nameLabel = nameLabel
        self.yieldLabel = yieldLabel
        self.vminLineEdit = vminLineEdit
        self.vmaxLineEdit = vmaxLineEdit
        self.vbox = vbox
        self.refreshDataset(dataset)
        vminLineEdit.editingFinished.connect(self.emitLimitsChanged)
        vmaxLineEdit.editingFinished.connect(self.emitLimitsChanged)
    def refreshDataset(self,dataset):
        self.nameLabel.setText(dataset.name)
        Ntot = len(dataset)
        vmin = numpy.min(dataset)
        vmax = numpy.max(dataset)
        yieldLabelString = "Yield: %.2f%% - %i/%i" % (100.,Ntot,Ntot)
        self.yieldLabel.setText(yieldLabelString)
        self.dataset = dataset
        (hist,edges) = numpy.histogram(dataset,bins=100)
        edges = (edges[:-1]+edges[1:])/2.0
        if self.histogram.itemPlot != None:
            self.histogram.removeItem(self.histogram.itemPlot)
        #self.histogram.clear()
        item = self.histogram.plot(edges,hist,fillLevel=0,fillBrush=QtGui.QColor(255, 255, 255, 128),antialias=True)
        item.getViewBox().setMouseEnabled(x=False,y=False)
        self.histogram.itemPlot = item
        self.histogram.region.setRegion([vmin,vmax])
        self.histogram.autoRange()
    def syncLimits(self):
        (vmin,vmax) = self.histogram.region.getRegion()
        self.vminLineEdit.setText("%.3e" % vmin)
        self.vmaxLineEdit.setText("%.3e" % vmax)
        self.emitLimitsChanged()
    def emitLimitsChanged(self,foo=None):
        data = numpy.array(self.dataset,dtype="float") 
        Ntot = len(data)
        vmin = float(self.vminLineEdit.text())
        vmax = float(self.vmaxLineEdit.text())
        Nsel = ( (data<=vmax)*(data>=vmin) ).sum()
        label = "Yield: %.2f%% - %i/%i" % (100*Nsel/(1.*Ntot),Nsel,Ntot)
        self.yieldLabel.setText(label)
        self.limitsChanged.emit(vmin,vmax)
    
