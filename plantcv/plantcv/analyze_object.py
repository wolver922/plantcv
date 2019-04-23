# Analyzes an object and outputs numeric properties

import os
import cv2
import numpy as np
from plantcv.plantcv import print_image
from plantcv.plantcv import plot_image
from plantcv.plantcv import params
from plantcv.plantcv import outputs


def analyze_object(img, obj, mask):
    """Outputs numeric properties for an input object (contour or grouped contours).

    Inputs:
    img             = RGB or grayscale image data for plotting
    obj             = single or grouped contour object
    mask            = Binary image to use as mask for moments analysis

    Returns:
    analysis_images = list of output images

    :param img: numpy.ndarray
    :param obj: list
    :param mask: numpy.ndarray
    :return analysis_images: list
    """

    params.device += 1

    # Valid objects can only be analyzed if they have >= 5 vertices
    if len(obj) < 5:
        return None, None, None

    ori_img = np.copy(img)
    # Convert grayscale images to color
    if len(np.shape(ori_img)) == 2:
        ori_img = cv2.cvtColor(ori_img, cv2.COLOR_GRAY2BGR)

    if len(np.shape(img)) == 3:
        ix, iy, iz = np.shape(img)
    else:
        ix, iy = np.shape(img)
    size = ix, iy, 3
    size1 = ix, iy
    background = np.zeros(size, dtype=np.uint8)
    background1 = np.zeros(size1, dtype=np.uint8)
    background2 = np.zeros(size1, dtype=np.uint8)

    # Check is object is touching image boundaries (QC)
    frame_background = np.zeros(size1, dtype=np.uint8)
    frame = frame_background + 1
    frame_contour, frame_hierarchy = cv2.findContours(frame, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)[-2:]
    ptest = []
    vobj = np.vstack(obj)
    for i, c in enumerate(vobj):
        xy = tuple(c)
        pptest = cv2.pointPolygonTest(frame_contour[0], xy, measureDist=False)
        ptest.append(pptest)
    in_bounds = all(c == 1 for c in ptest)

    # Convex Hull
    hull = cv2.convexHull(obj)
    hull_vertices = len(hull)
    # Moments
    #  m = cv2.moments(obj)
    m = cv2.moments(mask, binaryImage=True)
    # Properties
    # Area
    area = m['m00']

    if area:
        # Convex Hull area
        hull_area = cv2.contourArea(hull)
        # Solidity
        solidity = 1
        if int(hull_area) != 0:
            solidity = area / hull_area
        # Perimeter
        perimeter = cv2.arcLength(obj, closed=True)
        # x and y position (bottom left?) and extent x (width) and extent y (height)
        x, y, width, height = cv2.boundingRect(obj)
        # Centroid (center of mass x, center of mass y)
        cmx, cmy = (float(m['m10'] / m['m00']), float(m['m01'] / m['m00']))
        # Ellipse
        center, axes, angle = cv2.fitEllipse(obj)
        major_axis = np.argmax(axes)
        minor_axis = 1 - major_axis
        major_axis_length = float(axes[major_axis])
        minor_axis_length = float(axes[minor_axis])
        eccentricity = float(np.sqrt(1 - (axes[minor_axis] / axes[major_axis]) ** 2))

        # Longest Axis: line through center of mass and point on the convex hull that is furthest away
        cv2.circle(background, (int(cmx), int(cmy)), 4, (255, 255, 255), -1)
        center_p = cv2.cvtColor(background, cv2.COLOR_BGR2GRAY)
        ret, centerp_binary = cv2.threshold(center_p, 0, 255, cv2.THRESH_BINARY)
        centerpoint, cpoint_h = cv2.findContours(centerp_binary, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)[-2:]

        dist = []
        vhull = np.vstack(hull)

        for i, c in enumerate(vhull):
            xy = tuple(c)
            pptest = cv2.pointPolygonTest(centerpoint[0], xy, measureDist=True)
            dist.append(pptest)

        abs_dist = np.absolute(dist)
        max_i = np.argmax(abs_dist)

        caliper_max_x, caliper_max_y = list(tuple(vhull[max_i]))
        caliper_mid_x, caliper_mid_y = [int(cmx), int(cmy)]

        xdiff = float(caliper_max_x - caliper_mid_x)
        ydiff = float(caliper_max_y - caliper_mid_y)

        # Set default values
        slope = 1

        if xdiff != 0:
            slope = (float(ydiff / xdiff))
        b_line = caliper_mid_y - (slope * caliper_mid_x)

        if slope != 0:
            xintercept = int(-b_line / slope)
            xintercept1 = int((ix - b_line) / slope)
            if 0 <= xintercept <= iy and 0 <= xintercept1 <= iy:
                cv2.line(background1, (xintercept1, ix), (xintercept, 0), (255), params.line_thickness)
            elif xintercept < 0 or xintercept > iy or xintercept1 < 0 or xintercept1 > iy:
                # Used a random number generator to test if either of these cases were possible but neither is possible
                # if xintercept < 0 and 0 <= xintercept1 <= iy:
                #     yintercept = int(b_line)
                #     cv2.line(background1, (0, yintercept), (xintercept1, ix), (255), 5)
                # elif xintercept > iy and 0 <= xintercept1 <= iy:
                #     yintercept1 = int((slope * iy) + b_line)
                #     cv2.line(background1, (iy, yintercept1), (xintercept1, ix), (255), 5)
                # elif 0 <= xintercept <= iy and xintercept1 < 0:
                #     yintercept = int(b_line)
                #     cv2.line(background1, (0, yintercept), (xintercept, 0), (255), 5)
                # elif 0 <= xintercept <= iy and xintercept1 > iy:
                #     yintercept1 = int((slope * iy) + b_line)
                #     cv2.line(background1, (iy, yintercept1), (xintercept, 0), (255), 5)
                # else:
                yintercept = int(b_line)
                yintercept1 = int((slope * iy) + b_line)
                cv2.line(background1, (0, yintercept), (iy, yintercept1), (255), 5)
        else:
            cv2.line(background1, (iy, caliper_mid_y), (0, caliper_mid_y), (255), params.line_thickness)

        ret1, line_binary = cv2.threshold(background1, 0, 255, cv2.THRESH_BINARY)
        # print_image(line_binary,(str(device)+'_caliperfit.png'))

        cv2.drawContours(background2, [hull], -1, (255), -1)
        ret2, hullp_binary = cv2.threshold(background2, 0, 255, cv2.THRESH_BINARY)
        # print_image(hullp_binary,(str(device)+'_hull.png'))

        caliper = cv2.multiply(line_binary, hullp_binary)
        # print_image(caliper,(str(device)+'_caliperlength.png'))

        caliper_y, caliper_x = np.array(caliper.nonzero())
        caliper_matrix = np.vstack((caliper_x, caliper_y))
        caliper_transpose = np.transpose(caliper_matrix)
        caliper_length = len(caliper_transpose)

        caliper_transpose1 = np.lexsort((caliper_y, caliper_x))
        caliper_transpose2 = [(caliper_x[i], caliper_y[i]) for i in caliper_transpose1]
        caliper_transpose = np.array(caliper_transpose2)

    # else:
    #  hull_area, solidity, perimeter, width, height, cmx, cmy = 'ND', 'ND', 'ND', 'ND', 'ND', 'ND', 'ND'

    analysis_images = []

    # Draw properties
    if area:
        cv2.drawContours(ori_img, obj, -1, (255, 0, 0), params.line_thickness)
        cv2.drawContours(ori_img, [hull], -1, (255, 0, 255), params.line_thickness)
        cv2.line(ori_img, (x, y), (x + width, y), (255, 0, 255), params.line_thickness)
        cv2.line(ori_img, (int(cmx), y), (int(cmx), y + height), (255, 0, 255), params.line_thickness)
        cv2.line(ori_img, (tuple(caliper_transpose[caliper_length - 1])), (tuple(caliper_transpose[0])), (255, 0, 255),
                 params.line_thickness)
        cv2.circle(ori_img, (int(cmx), int(cmy)), 10, (255, 0, 255), params.line_thickness)
        # Output images with convex hull, extent x and y
        # out_file = os.path.splitext(filename)[0] + '_shapes.jpg'
        # out_file1 = os.path.splitext(filename)[0] + '_mask.jpg'

        # print_image(ori_img, out_file)
        analysis_images.append(ori_img)

        # print_image(mask, out_file1)
        analysis_images.append(mask)

    else:
        pass

    outputs.add_measurement(variable='pixel_area', trait='area',
                            method='plantcv.plantcv.analyze_object', scale='pixels', datatype=int,
                            value=area, label='pixels')
    outputs.add_measurement(variable='area', trait='convex hull area',
                            method='plantcv.plantcv.analyze_object', scale='pixels', datatype=int,
                            value=hull_area, label='pixels')
    outputs.add_measurement(variable='solidity', trait='object area divided by convex hull area',
                            method='plantcv.plantcv.analyze_object', scale='none', datatype=float,
                            value=solidity, label='none')
    outputs.add_measurement(variable='perimeter', trait='object perimeter length',
                            method='plantcv.plantcv.analyze_object', scale='pixels', datatype=int,
                            value=perimeter, label='pixels')
    outputs.add_measurement(variable='width', trait='maximum object width',
                            method='plantcv.plantcv.analyze_object', scale='pixels', datatype=int,
                            value=width, label='pixels')
    outputs.add_measurement(variable='height', trait='maximum object width',
                            method='plantcv.plantcv.analyze_object', scale='pixels', datatype=int,
                            value=height, label='pixels')
    outputs.add_measurement(variable='longest_axis', trait='longest path between convex hull vertices through the '
                                                           'center of mass',
                            method='plantcv.plantcv.analyze_object', scale='pixels', datatype=int,
                            value=caliper_length, label='pixels')
    outputs.add_measurement(variable='center-of-mass-x', trait='x-axis coordinate of the object center of mass',
                            method='plantcv.plantcv.analyze_object', scale='none', datatype=int,
                            value=cmx, label='none')
    outputs.add_measurement(variable='center-of-mass-y', trait='y-axis coordinate of the object center of mass',
                            method='plantcv.plantcv.analyze_object', scale='none', datatype=int,
                            value=cmy, label='none')
    outputs.add_measurement(variable='hull_vertices', trait='number of convex hull vertices',
                            method='plantcv.plantcv.analyze_object', scale='none', datatype=int,
                            value=hull_vertices, label='none')
    outputs.add_measurement(variable='in_bounds', trait='is the object touching the border of the image',
                            method='plantcv.plantcv.analyze_object', scale='none', datatype=bool,
                            value=in_bounds, label='none')
    outputs.add_measurement(variable='ellipse_center_x', trait='x-axis coord of center of the minimum bounding ellipse',
                            method='plantcv.plantcv.analyze_object', scale='none', datatype=int,
                            value=center[0], label='none')
    outputs.add_measurement(variable='ellipse_center_y', trait='y-axis coord of center of the minimum bounding ellipse',
                            method='plantcv.plantcv.analyze_object', scale='none', datatype=int,
                            value=center[1], label='none')
    outputs.add_measurement(variable='ellipse_major_axis', trait='length of major axis of the minimum bounding ellipse',
                            method='plantcv.plantcv.analyze_object', scale='pixels', datatype=int,
                            value=major_axis_length, label='pixels')
    outputs.add_measurement(variable='ellipse_minor_axis', trait='length of minor axis of the minimum bounding ellipse',
                            method='plantcv.plantcv.analyze_object', scale='pixels', datatype=int,
                            value=minor_axis_length, label='pixels')
    outputs.add_measurement(variable='ellipse_angle', trait='degrees of rotation of the bounding ellipse major axis',
                            method='plantcv.plantcv.analyze_object', scale='degrees', datatype=float,
                            value=float(angle), label='degrees')
    outputs.add_measurement(variable='ellipse_eccentricity', trait='eccentricity of the bounding ellipse',
                            method='plantcv.plantcv.analyze_object', scale='degrees', datatype=float,
                            value=float(eccentricity), label='degrees')

    if params.debug is not None:
        cv2.drawContours(ori_img, obj, -1, (255, 0, 0), params.line_thickness)
        cv2.drawContours(ori_img, [hull], -1, (255, 0, 255), params.line_thickness)
        cv2.line(ori_img, (x, y), (x + width, y), (255, 0, 255), params.line_thickness)
        cv2.line(ori_img, (int(cmx), y), (int(cmx), y + height), (255, 0, 255), params.line_thickness)
        cv2.circle(ori_img, (int(cmx), int(cmy)), 10, (255, 0, 255), params.line_thickness)
        cv2.line(ori_img, (tuple(caliper_transpose[caliper_length - 1])), (tuple(caliper_transpose[0])), (255, 0, 255),
                 params.line_thickness)
        if params.debug == 'print':
            print_image(ori_img, os.path.join(params.debug_outdir, str(params.device) + '_shapes.jpg'))
        elif params.debug == 'plot':
            if len(np.shape(img)) == 3:
                plot_image(ori_img)
            else:
                plot_image(ori_img, cmap='gray')

    # Store images
    outputs.images.append(analysis_images)
    return analysis_images
