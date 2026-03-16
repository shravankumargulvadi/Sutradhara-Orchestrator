cmake_minimum_required(VERSION 3.8)
project(robot_control_interfaces)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)

set(msg_files
  "msg/Point2D.msg"
  "msg/CapabilityProfile.msg"
  "msg/RobotState.msg"
  "msg/TaskConstraints.msg"
  "msg/TaskSuccessCriteria.msg"
  "msg/TaskTarget.msg"
  "msg/TaskSpec.msg"
  "msg/TaskCommand.msg"
)

rosidl_generate_interfaces(${PROJECT_NAME}
  ${msg_files}
)

ament_export_dependencies(rosidl_default_runtime)

ament_package()
