# xEdgeSim Sensor Node Firmware
# Minimal Zephyr application for device-tier emulation

cmake_minimum_required(VERSION 3.20.0)

find_package(Zephyr REQUIRED HINTS $ENV{ZEPHYR_BASE})
project(sensor_node VERSION 1.0.0)

# Application sources
target_sources(app PRIVATE
    src/main.c
)
