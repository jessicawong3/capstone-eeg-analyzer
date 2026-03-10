# EEG Analyzer Dashboard
This interactive dashboard is a Python-based graphical interface running on the host PC, handling visualization, control, and monitoring of EEG signals. 


## To start the DASHBOARD:
- Make sure you are in folder "dashboard" (`cd dashboard`)
- Run it! (`python3 ./main.py`)
  

## Tools
The dashboard is built using **PyQt** for the Graphical User Interface (GUI), and **PyQtGraph**, a pure-python graphics and GUI library intended for use in mathematics, scientific, and engineering applications. EEG data is loaded and preprocessed via **MNE-Python**, a library intended for exploring, visualizing, and analyzing human neurophysiological data.


## Interaction with system

This dashboard is intended to be used as a subsystem of a proof-of-concept system designed for classification/analysis to make access to EEG technology achievable without proprietary hardware/software constraints. The greater system uses an STM32 NUCLEO-F446ZE MCU to host signal generation, a Zynq-7020 FPGA to host signal processing, and an ML model for classifications.

Using these technologies, the dashboard displays real-time EEG waveforms, wavelet transformation outputs, predicted sleep stages, and other relevant statistics. 

The dashboard also allows the user to control and interact with each module, such as toggling between real data and synthetic modes in the input block and selecting which data to stream to the dashboard. This dashboard provides an accessible and interactive front end for education and demonstration, closing the loop by showing the full system behavior in real-time.



