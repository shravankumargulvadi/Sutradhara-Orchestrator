#include "geometry_msgs/msg/pose_array.hpp"
#include "rclcpp/rclcpp.hpp"
#include "robot_control_interfaces/msg/task_command.hpp"
#include "robot_control_interfaces/msg/task_target.hpp"

#include <memory>
#include <string>
#include <unordered_map>

class MissionControlNode : public rclcpp::Node
{
public:
    MissionControlNode() : Node("mission_control_node")
    {
        this->declare_parameter<double>("flight_altitude_m", 8.0);
        flight_altitude_m_ = this->get_parameter("flight_altitude_m").as_double();

        task_command_sub_ =
            this->create_subscription<robot_control_interfaces::msg::TaskCommand>(
                "/orchestrator/task_command",
                10,
                std::bind(&MissionControlNode::task_command_callback, this, std::placeholders::_1));
    }

private:
    using PoseArrayPublisher = rclcpp::Publisher<geometry_msgs::msg::PoseArray>::SharedPtr;

    std::unordered_map<std::string, PoseArrayPublisher> trajectory_publishers_;
    rclcpp::Subscription<robot_control_interfaces::msg::TaskCommand>::SharedPtr task_command_sub_;
    double flight_altitude_m_;

    static std::string normalize_robot_id(const std::string &robot_id)
    {
        if (robot_id.empty()) {
            return {};
        }

        if (robot_id.front() == '/') {
            return robot_id;
        }

        return "/" + robot_id;
    }

    PoseArrayPublisher get_or_create_publisher(const std::string &robot_ns)
    {
        auto it = trajectory_publishers_.find(robot_ns);
        if (it != trajectory_publishers_.end()) {
            return it->second;
        }

        const std::string topic = robot_ns + "/trajectory_upload";
        auto publisher = this->create_publisher<geometry_msgs::msg::PoseArray>(topic, 10);
        trajectory_publishers_.emplace(robot_ns, publisher);
        RCLCPP_INFO(this->get_logger(), "Created trajectory publisher for %s", topic.c_str());
        return publisher;
    }

    geometry_msgs::msg::PoseArray build_pose_array(
        const robot_control_interfaces::msg::TaskCommand &command) const
    {
        geometry_msgs::msg::PoseArray trajectory;
        trajectory.header.stamp = this->now();
        trajectory.header.frame_id = command.task.target.frame.empty() ? "map" : command.task.target.frame;

        for (const auto &point : command.task.target.points) {
            geometry_msgs::msg::Pose pose;
            pose.position.x = point.x;
            pose.position.y = point.y;
            pose.position.z = -flight_altitude_m_;
            pose.orientation.w = 1.0;
            trajectory.poses.push_back(pose);
        }

        return trajectory;
    }

    void task_command_callback(const robot_control_interfaces::msg::TaskCommand::SharedPtr msg)
    {
        const std::string robot_ns = normalize_robot_id(msg->robot_id);
        if (robot_ns.empty()) {
            RCLCPP_WARN(this->get_logger(), "Received TaskCommand with empty robot_id");
            return;
        }

        if (msg->type != robot_control_interfaces::msg::TaskCommand::ASSIGN) {
            RCLCPP_INFO(
                this->get_logger(),
                "Ignoring TaskCommand type %u for %s: not implemented yet",
                msg->type,
                robot_ns.c_str());
            return;
        }

        const auto &target = msg->task.target;
        if (target.kind != robot_control_interfaces::msg::TaskTarget::POINT &&
            target.kind != robot_control_interfaces::msg::TaskTarget::REGION) {
            RCLCPP_WARN(
                this->get_logger(),
                "Ignoring TaskCommand %s for %s: unsupported target kind %u",
                msg->command_id.c_str(),
                robot_ns.c_str(),
                target.kind);
            return;
        }

        if (target.points.empty()) {
            RCLCPP_WARN(
                this->get_logger(),
                "Ignoring TaskCommand %s for %s: target contains no points",
                msg->command_id.c_str(),
                robot_ns.c_str());
            return;
        }

        auto publisher = get_or_create_publisher(robot_ns);
        auto trajectory = build_pose_array(*msg);
        publisher->publish(trajectory);

        RCLCPP_INFO(
            this->get_logger(),
            "Published %zu waypoint(s) for robot %s from task %s",
            trajectory.poses.size(),
            robot_ns.c_str(),
            msg->task_id.c_str());
    }
};

int main(int argc, char **argv)
{
    rclcpp::init(argc, argv);
    rclcpp::spin(std::make_shared<MissionControlNode>());
    rclcpp::shutdown();
    return 0;
}
