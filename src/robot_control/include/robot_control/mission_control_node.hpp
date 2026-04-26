#pragma once

#include "rclcpp/node_options.hpp"
#include "rclcpp/rclcpp.hpp"

class MissionControlNode : public rclcpp::Node
{
public:
    explicit MissionControlNode(const rclcpp::NodeOptions &options = rclcpp::NodeOptions());
};
