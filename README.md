# Controls for prototype reconfigurable CubeSats

This project houses the code for testing functionality of our prototype electromagnetically-actuated CubeSats.

## Current TODO list:
- [ ] Research and implement single server, multiple client communication between rpis and master
- [ ] Implement software PWM for controlling EMs (In cubesat\_client.py)
- [ ] Add ToF sensor library to requirements.txt and incorporate sensor readings
- [ ] Create test script to run a single rotation and log data (send sensor data over socket connection to master, save locally)
