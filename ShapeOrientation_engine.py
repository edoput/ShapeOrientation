##Polygones=vector polygon
##Interval_Angle= number
##Export=output directory

from qgis.core import *
from qgis.utils import *
from qgis.gui import *

from PyQt4.QtCore import *
from PyQt4.QtGui import *

import csv
from math import pi, atan

import numpy as np
import matplotlib.pyplot as plt
from pylab import *
from pylab import hist


# F.Fouriaux juillet 2017


# # # # Fonctions # # # #
# F Gisement(point1, point2) --> Return Gisement
def Gisement(a, b):
    deltax = a[0]-b[0]
    signex = deltax/abs(deltax)
    deltay = a[1]-b[1]
    if deltay == 0:
        theta = pi + (pi/2 * signex)
    else:
        theta = atan(deltax/deltay)
    if deltax <= 0 and deltay <= 0:
        gis = theta
    elif deltax >= 0 and deltay <= 0:
        gis = theta
    else:
        gis = theta + pi
    if gis < 0:
        gis = 2*pi + gis
    return gis


# F MinRect(polygone,point)  --> Return Polygon minimum, rectangle minimum,
# orientation of the great axis
def MinRect(hull, centre):
    """
    inRect(polygone,point)  -->
    Return Polygon minimum, rectangle minimum, orientation of the great axis
    """
    n = len(hull.asPolygon()[0])
    aires = []
    gisement = 0.0
    rotation = 0.0
    orient = 0.0
    for i in range(n-1):
        # azimuth computation
        gisement = Gisement(
                hull.asPolygon()[0][i],
                hull.asPolygon()[0][i+1]
                )
        # Record the rotations
        rotation = rotation + gisement
        # inverse rotation of the azimuth
        hull.rotate(-1*180*gisement/pi, centre)
        # creation of the bounding box
        bboxrect = hull.boundingBox()
        # compute bbox's area
        airebbox = bboxrect.width() * bboxrect.height()
        # store it for later comparison
        aires.append(airebbox)
        if airebbox == min(aires):
            if bboxrect.xMaximum()-bboxrect.xMinimum() <= bboxrect.yMaximum() - bboxrect.yMinimum():
                # select as major axis
                orient = rotation
            else:
                orient = rotation + (pi/2)
            if orient >= 2*pi:
                # Angle between 0 and 360 degree
                n = int(orient/(2*pi))
                orient = orient-(n*2*pi)
            if orient > pi:
                # Azimut between 0 and 180 degree
                # because we can't know the direction
                orient = orient-pi

    return orient


# F DiagGenerator (angles,interval) --> Show a matplotlib rose diagram of orientation
def DiagGenerator(angles, inter, theta, interval, colorRamp):
    #progress bar initialisation
    iface.messageBar().clearWidgets()
    progressMessageBar = iface.messageBar().createMessage("Creation of the diagram ...")
    progress = QProgressBar()
    progress.setMaximum(100)
    progressMessageBar.layout().addWidget(progress)
    iface.messageBar().pushWidget(
        progressMessageBar,
        iface.messageBar().INFO
    )
    # frequency
    histo = hist(angles, inter)[0]
    r = histo.tolist()
    # fake plot to get the color bar
    plot = plt.scatter(
        r,
        r,
        c=r,
        cmap=colorRamp+'_r'
    )
    plt.clf()
    #colorRamp
    cr = cm.get_cmap(name=colorRamp+'_r')
    # diagram
    ax = plt.subplot(
        111,
        projection='polar'
    )
    colors = cr(histo/float(max(histo)))
    larg = interval * pi/180
    ax.bar(
        theta,
        r,
        width=larg,
        color=colors,
        align='center',
        edgecolor='black',
    )
    ax.set_rmax(max(r))
    ticks = np.arange(0, max(r), max(r)/4)
    ax.set_rticks(ticks)  # less radial ticks
    ax.set_rlabel_position(-22.5)  # get radial labels away from plotted line
    ax.set_theta_direction(-1)
    ax.set_theta_zero_location("N")
    ax.grid(True)

    plt.colorbar(plot)
    ax.set_title(
        "Frequence des orientations",
        va='bottom',
    )
    progress.setValue(100)
    plt.show()


def DiagOrientPolyg(poly, interval, table, diagr, colorRamp, Id):
    polygones = QgsVectorLayer(poly, "polygones", "ogr")
    poly_prov = polygones.dataProvider()
    # Csv File for orientation record
    with open(table, 'w') as out:
        writer = csv.DictWriter(out, ['id', 'orientation'])
        fPolyg = polygones.getFeatures()
        angles = []
        # intervals on the circle
        inter = np.arange(0, 361, interval)
        inter = [i*pi/180 for i in inter]
        theta = inter[0:-1]
        #number of iteration for progress bar
        ntot = polygones.featureCount()
        #progress bar initialisation
        iface.messageBar().clearWidgets()
        progressMessageBar = iface.messageBar().createMessage("Computation of directions ...")
        progress = QProgressBar()
        progress.setMaximum(100)
        progressMessageBar.layout().addWidget(progress)
        iface.messageBar().pushWidget(
            progressMessageBar,
            iface.messageBar().INFO,
        )
        # Loop on geometries
        for i, feature in enumerate(fPolyg):
            progress.setValue(i/ntot*100)
            geomPolyg = feature.geometry()
            Aire = geomPolyg.area()
            Idf = str(feature.attribute(Id))
            # ConvexHull and centroid of the polygon
            hullPolyg = geomPolyg.convexHull()
            centroidPolyg = geomPolyg.centroid().asPoint()

            gist = MinRect(hullPolyg, centroidPolyg)
            writer.writerow({'id': Idf, 'orientation': gist * 180/pi})
            angles.append(gist)

    if diagr is True:
        DiagGenerator(
            angles,
            inter,
            theta,
            interval,
            colorRamp,
        )


def DiagOrientLine(line, interval, table, diagr, colorRamp, Id):
    lines = QgsVectorLayer(line, "lines", "ogr")
    lines_prov = lines.dataProvider()

    # Csv File for orientation record
    with open(table, 'w') as out:
        writer = csv.DictWriter(out, ['id', 'orientation'])
        writer.writeheader()

        angles = []
        # intervals on the circle
        inter = np.arange(0, 361, interval)
        inter = [i*pi/180 for i in inter]
        theta = inter[0:-1]

        for feature in lines.getFeatures():
            polyline = feature.geometry().asPolyline()
            try:
                gist = Gisement(polyline[0], polyline[-1])
                angles.append(gist)
            except IndexError:
                gist = float('nan')

            writer.writerow({
                'id': feature.attribute(Id),
                'orientation': gist * 180/pi,
            })

    if diagr is True:
        DiagGenerator(
            angles,
            inter,
            theta,
            interval,
            colorRamp,
        )
