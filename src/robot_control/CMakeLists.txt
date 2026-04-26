cmake_minimum_required(VERSION 3.8)
project(robot_control)

# Default to C++17
if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 17)
endif()

# Add compile options, if using GCC or Clang
if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# Find required packages
find_package(ament_cmake REQUIRED)
find_package(ament_index_cpp REQUIRED)
find_package(ament_cmake_gtest REQUIRED)
find_package(rclcpp REQUIRED)
find_package(px4_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(std_msgs REQUIRED)
find_package(robot_control_interfaces REQUIRED)
find_package(yaml-cpp REQUIRED)

# Add your executable
add_executable(uav_manager src/uav_manager.cpp)

# Specify dependencies for your executable
ament_target_dependencies(uav_manager
  ament_index_cpp
  rclcpp
  px4_msgs
  geometry_msgs
  std_msgs
  robot_control_interfaces
)

target_link_libraries(uav_manager
  yaml-cpp::yaml-cpp
)

add_library(sector_route_registry_lib src/sector_route_registry.cpp)

target_link_libraries(sector_route_registry_lib
  yaml-cpp::yaml-cpp
)

target_include_directories(sector_route_registry_lib PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>
)

add_library(mission_control_node_lib src/mission_control_node.cpp)

ament_target_dependencies(mission_control_node_lib
  ament_index_cpp
  rclcpp 
  std_msgs 
  geometry_msgs
  robot_control_interfaces
)

target_link_libraries(mission_control_node_lib
  sector_route_registry_lib
)

target_include_directories(mission_control_node_lib PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>
)

add_executable(mission_control_node src/mission_control_main.cpp)

ament_target_dependencies(mission_control_node
  rclcpp
)

target_link_libraries(mission_control_node
  mission_control_node_lib
)

# Install the executable
install(TARGETS
  mission_control_node_lib
  sector_route_registry_lib
  uav_manager
  mission_control_node
  DESTINATION lib/${PROJECT_NAME}
)

install(DIRECTORY include/
  DESTINATION include
)

if(BUILD_TESTING)
  ament_add_gtest(test_mission_control test/test_mission_control.cpp)
  if(TARGET test_mission_control)
    target_link_libraries(test_mission_control sector_route_registry_lib)
  endif()
endif()

# Necessary for ROS2 package
ament_package()
