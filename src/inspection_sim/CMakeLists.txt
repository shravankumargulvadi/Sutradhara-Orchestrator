cmake_minimum_required(VERSION 3.8)
project(inspection_sim)

find_package(ament_cmake REQUIRED)

install(
  DIRECTORY
    worlds
    models
    config
    launch
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
