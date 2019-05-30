# Team 'ApplePi' from Jaslo, Poland

from picamera.array import PiRGBArray
from picamera import PiCamera
from sense_hat import SenseHat
from logzero import logger
from time import sleep
import datetime
import numpy as np
import time
import cv2
import logging
import logzero
import ephem
import os

# Setting the global variables
sense = SenseHat()
dir_path = os.path.dirname(os.path.realpath(__file__))
photo_counter = 1

# Setting up the camera
camera = PiCamera()
camera.resolution = (1600, 912)  

# Latest TLE data for ISS location
name = "ISS (ZARYA)"
line1 = "1 25544U 98067A   19027.92703822  .00001504  00000-0  30922-4 0  9992"
line2 = "2 25544  51.6413 338.8011 0004969 323.5710 139.9801 15.53200917153468"
iss = ephem.readtle(name, line1, line2)

# Setting the logfile name
logzero.logfile(dir_path+"/data01.csv")

# Setting a custom formatter
formatter = logging.Formatter('%(asctime)-15s %(levelname)s: %(message)s');
logzero.formatter(formatter)
info = "photo_counter, lat, lon, direct1, direct2, water_per, cloud_per, land_per, season"
logger.info(info)

# Main display
def matrix_Run():                              
        G = (0, 85, 0)
        R = (85, 0, 0)
        X = (85, 33, 33)
        Y = (66, 0, 0)
        B = (34, 17, 0)
        O = (0,0,0)
        
        logo = [
        O, G, G, O, O, O, O, O,
        O, O, G, G, B, O, O, O,
        O, R, R, R, R, R, R, O,
        Y, R, R, R, R, X, R, Y,
        Y, R, R, R, R, R, X, Y,
        Y, R, R, R, R, R, R, Y,
        O, Y, R, R, R, R, Y, O,
        O, O, Y, Y, Y, Y, O, O,
        ]

        return logo

# Displaying percentage of water, clouds and land shown in the photo   
def matrix_proportions(waterper, cloudper):                              
        L = (0, 70, 0)
        W = (0, 0, 70)
        C = (75, 75, 75)
        O = (0, 0, 0)

        matrix = [
        O, O, O, O, O, O, O, O,
        L, L, L, L, L, L, L, L,
        L, L, L, L, L, L, L, L,
        L, L, L, L, L, L, L, L,
        L, L, L, L, L, L, L, L,
        L, L, L, L, L, L, L, L,
        L, L, L, L, L, L, L, L,
        O, O, O, O, O, O, O, O,
        ]

        waterprop = int(round(48*waterper, 0) + 8)
        cloudprop = int(round(48*cloudper, 0) + 8)

        for x in range(8, waterprop):
                matrix[x] = W
                
        for x in range(waterprop, cloudprop + waterprop - 8):
                matrix[x] = C

        return matrix

# Displaying the Moon
def matrix_moon():                              
        O = (25, 0, 60)
        M = (70, 70, 70)

        matrix = [
        O, O, O, M, M, O, O, O,
        O, O, M, M, O, O, O, O,
        O, M, M, O, O, O, O, O,
        O, M, M, O, O, O, O, O,
        O, M, M, O, O, O, O, O,
        O, M, M, O, O, O, O, O,
        O, O, M, M, O, O, O, O,
        O, O, O, M, M, O, O, O,
        ]

        return matrix

# Function which is writing latitude/longitude to EXIF data for photographs  
def get_latlon():
        iss.compute()
        long_value = [float(i) for i in str(iss.sublong).split(":")]
        if long_value[0] < 0:
                long_value[0] = abs(long_value[0])
                camera.exif_tags['GPS.GPSLongitudeRef'] = "W"
                direction1 = "W"
        else:
                camera.exif_tags['GPS.GPSLongitudeRef'] = "E"
                direction1 = "E"
        camera.exif_tags['GPS.GPSLongitude'] = '%d/1,%d/1,%d/10' % (long_value[0], long_value[1], long_value[2]*10)
        lat_value = [float(i) for i in str(iss.sublat).split(":")]
        if lat_value[0] < 0:
                lat_value[0] = abs(lat_value[0])
                camera.exif_tags['GPS.GPSLatitudeRef'] = "S"
                direction2 = "S"
        else:
                camera.exif_tags['GPS.GPSLatitudeRef'] = "N"
                direction2 = "N"
        camera.exif_tags['GPS.GPSLatitude'] = '%d/1,%d/1,%d/10' % (lat_value[0], lat_value[1], lat_value[2]*10)
        return(str(lat_value), str(long_value), str(direction1), str(direction2))

# Water, clouds and land detection
def water_detection(hsv, image, season):
        # Water detection
        low_blue = np.array([40,90,0])
        high_blue = np.array([250,255,150])
        mask_blue = cv2.inRange(hsv, low_blue, high_blue)   # Creating a mask with marked water
        mask_blue1 = cv2.bitwise_not(mask_blue) 
        cv2.circle(mask_blue1,(828,450), 811, (250,250,250), 260)
                
        waterper = ((1459200 - np.count_nonzero(mask_blue1))/1139704)   # Calculating water percentage
                
        water_image = cv2.bitwise_and(image, image, mask=mask_blue1)
        water_image[np.where((water_image==[0,0,0]).all(axis=2))] = [200,20,20] 

        # Clouds detection     
        low_white = np.array([1,1,150])
        high_white = np.array([250,50,255])
        mask_white = cv2.inRange(hsv, low_white, high_white)   # Creating a mask with marked clouds
        mask_white1 = cv2.bitwise_not(mask_white)
        cv2.circle(mask_white1,(828,450), 811, (250,250,250), 260)
                
        cloudper = ((1459200 - np.count_nonzero(mask_white1))/1139704)  # Calculating clouds percentage

        cloud_image = cv2.bitwise_and(water_image, water_image, mask=mask_white1)
        cloud_image[np.where((cloud_image==[0,0,0]).all(axis=2))] = [255,255,255]

        # Land detection
        land = cv2.bitwise_and(mask_white1, mask_blue1)   # Creating a mask with marked land
        land1 = cv2.bitwise_not(land)
        cv2.circle(land1,(828,450), 811, (255,255,255), 260)

        landper = (1459200-np.count_nonzero(land1))/1139704   # Calculating land percentage

        land_image = cv2.bitwise_and(cloud_image, cloud_image, mask=land1)
        land_image[np.where((land_image==[0,0,0]).all(axis=2))] = [26,150,96]

        # Creating mask with drawn coasts
        water_edge = cv2.Laplacian(mask_blue1, cv2.CV_8U)
        water_edge1 = cv2.bitwise_not(water_edge)
        cv2.circle(water_edge1,(828,450), 811, (255,255,255), 260)

        edge_image = cv2.bitwise_and(image, image, mask=water_edge1)
        edge_image[np.where((edge_image==[0,0,0]).all(axis=2))] = [0,0,255]

        # Showing the percentage of water, clouds and land on the photo
        water_per = str(round(100*waterper, 1))
        cloud_per = str(round(100*cloudper, 1))
        land_per = str(round(100*landper, 1))

        if season == "night":
                # Saving the image with marked water, clouds and land and coasts
                cv2.imwrite(dir_path+"/night_detection_image_"+ str(photo_counter).zfill(3)+".jpg",land_image)
                cv2.imwrite(dir_path+"/night_edge_image_"+ str(photo_counter).zfill(3)+".jpg",edge_image)            
        else:
                sense.set_pixels(matrix_proportions(waterper, cloudper))
                
                # Saving the image with marked water, clouds and land and coasts
                cv2.imwrite(dir_path+"/detection_image_"+ str(photo_counter).zfill(3)+".jpg",land_image)
                cv2.imwrite(dir_path+"/edge_image_"+ str(photo_counter).zfill(3)+".jpg",edge_image)

        return(water_per, cloud_per, land_per)

# Image processing 
def image_processing():
        camera.capture(dir_path+"/image_"+ str(photo_counter).zfill(3)+".jpg")  # Taking a photo    

        image = cv2.imread(dir_path+"/image_"+ str(photo_counter).zfill(3)+".jpg")  # Loading the photo
        image[np.where((image==[0,0,0]).all(axis=2))] = [1,1,1]

        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

        # Night detection
        low_grey = np.array([0,0,0])
        high_grey = np.array([255,125,95])
        mask_grey = cv2.inRange(hsv, low_grey, high_grey)
        cv2.circle(mask_grey,(828,450), 811, (250,250,250), 260)
        greyper = ((1459200 - np.count_nonzero(mask_grey))/1139704)

        if greyper > 0.65:
                season = "night"
                sense.set_pixels(matrix_moon())
                water_per, cloud_per, land_per = water_detection(hsv, image, season,)
        else:
                season = "day"
                water_per, cloud_per, land_per = water_detection(hsv, image, season,)
                
        return(water_per, cloud_per, land_per, season)

# Main program
start_time = datetime.datetime.now()    # Datetime variable to store the start time
now_time = datetime.datetime.now()      # Datetime variable to store the current time

sense.set_pixels(matrix_Run())    # Displaying our logo

while (now_time < start_time + datetime.timedelta(minutes=175)):  
        try:
                lat, lon, direct1, direct2 = get_latlon() # Getting latitude and longitude
                
                water_per, cloud_per, land_per, season = image_processing()
                
                # Saving the data to the file
                logger.info("%s,%s,%s,%s,%s,%s,%s,%s,%s", photo_counter, lat, lon, direct1, direct2, water_per, cloud_per, land_per, season)        
                
                sleep(12)
                sense.set_pixels(matrix_Run())
                sleep(6)

                photo_counter += 1
                now_time = datetime.datetime.now()      # Updating current time
        except Exception as e:
                logger.error("Experiment error: " + str(e))

sense.clear()
















