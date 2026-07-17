# Introduction

Welcome to the Unitree Go2 Sim-to-Real guide. This documentation walks you through the complete workflow—from policy training in simulation to Sim-to-Sim validation and deployment on a real robot.  

The **MuJoCo Playground** and **IsaacLab** sections follow the same overall pipeline: 

- Train a PPO policy in simulation
- Validate it through sim-to-sim transfer
- Deploy it on the Unitree Go2

The main difference is the simulation platform used for training.  
The **Real-World Setup** section covers the required robot hardware, onboard computing configuration, and instructions for flashing the NVIDIA Jetson AGX Orin.

Follow the sections in order to build, validate, and deploy your own Sim-to-Real locomotion pipeline.