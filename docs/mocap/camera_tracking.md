# Camera Tracking 

Refer to Qualisys Motion Capture system

Install [Qualisys Track Manager](https://www.qualisys.com/software/qualisys-track-manager/) on Windows system  
Install [Qualisys ROS2 driver](https://github.com/MOCAP4ROS2-Project/mocap4ros2_qualisys) on Linux system

## Get started with Qualisys Track Manager
1. Open an existing project by locating to the corresponding folder.  
2. Start by clicking on `new`. A blank page will appear.  
Make sure no markers are now in the coverage of qualisys, and then click on `Auto-Mask` to remove noise.  
Click on `3D`, place the cap on the ground and check if it can be found in `3D` view.


## Launching Qualisys ROS2 driver and collect data
1. Clone and build the driver  
2. Set host_name in file `mocap_ws/src/mocap4ros2_qualisys/qualisys_driver/config/qualisys_driver_params.yaml` to the local WiFi IP address    
3. Connect to the local WiFi   
4. Commands to launch node and record data:
```sh
ros2 launch qualisys_driver qualisys.launch.py 
ros2 run rviz2 rviz2 # visualization if message `tf` is available. Add `tf` to the displays and change the basic frame to world. Names of objects will be shown besides the coordinates
ros2 bag record -o /path/and/bag/name /rigid_bodies /markers
```