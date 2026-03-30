#include "ament_index_cpp/get_package_share_directory.hpp"
#include "geometry_msgs/msg/pose_array.hpp"
#include "px4_msgs/msg/offboard_control_mode.hpp"
#include "px4_msgs/msg/trajectory_setpoint.hpp"
#include "px4_msgs/msg/vehicle_command.hpp"
#include "px4_msgs/msg/vehicle_local_position.hpp"
#include "px4_msgs/msg/vehicle_status.hpp"
#include "rclcpp/rclcpp.hpp"
#include "robot_control_interfaces/msg/capability_profile.hpp"
#include "robot_control_interfaces/msg/robot_state.hpp"
#include "robot_control_interfaces/msg/task_ack.hpp"
#include "robot_control_interfaces/msg/task_command.hpp"
#include "robot_control_interfaces/msg/task_spec.hpp"
#include "robot_control_interfaces/msg/task_target.hpp"
#include "robot_control_interfaces/msg/task_update.hpp"
#include "yaml-cpp/yaml.h"

#include <array>
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <ctime>
#include <filesystem>
#include <iomanip>
#include <optional>
#include <sstream>
#include <string>
#include <unordered_map>
#include <vector>

using namespace std::chrono_literals;

namespace
{

std::string resolve_default_config_path(const std::string &filename)
{
    const auto share_dir = ament_index_cpp::get_package_share_directory("inspection_sim");
    return (std::filesystem::path(share_dir) / "config" / filename).string();
}

std::string iso_timestamp_now()
{
    const auto now = std::chrono::system_clock::now();
    const auto time = std::chrono::system_clock::to_time_t(now);
    std::tm utc_time{};
#if defined(_WIN32)
    gmtime_s(&utc_time, &time);
#else
    gmtime_r(&time, &utc_time);
#endif
    std::ostringstream oss;
    oss << std::put_time(&utc_time, "%Y-%m-%dT%H:%M:%S+00:00");
    return oss.str();
}

struct TaskContext
{
    std::string mission_id;
    std::string task_id;
    std::string command_id;
    std::string robot_id;
    uint8_t task_type{};
    uint8_t target_kind{};
    std::string sector_id;
    std::string asset_id;

    static TaskContext from_command(const robot_control_interfaces::msg::TaskCommand &command)
    {
        TaskContext context;
        context.mission_id = command.mission_id;
        context.task_id = command.task_id;
        context.command_id = command.command_id;
        context.robot_id = command.robot_id;
        context.task_type = command.task.task_type;
        context.target_kind = command.task.target.kind;
        context.sector_id = command.task.target.sector_id;
        context.asset_id = command.task.target.asset_id;
        return context;
    }
};

}  // namespace

enum class FlightState { WAITING, TAKING_OFF, HOVERING, FOLLOWING_TRAJECTORY };

class UavManager : public rclcpp::Node
{
public:
    UavManager() : Node("uav_manager")
    {
        this->declare_parameter<int>("drone_id", 0);
        this->declare_parameter<std::string>("assets_file", resolve_default_config_path("assets.yaml"));
        this->declare_parameter<std::string>("sectors_file", resolve_default_config_path("sectors.yaml"));
        this->get_parameter("drone_id", drone_id_);
        assets_file_ = this->get_parameter("assets_file").as_string();
        sectors_file_ = this->get_parameter("sectors_file").as_string();

        load_anomaly_config();

        robot_id_ = "px4_" + std::to_string(drone_id_);
        std::string ns = "/" + robot_id_;

        std::string offboard_topic = ns + "/fmu/in/offboard_control_mode";
        std::string trajectory_topic = ns + "/fmu/in/trajectory_setpoint";
        std::string vehicle_cmd_topic = ns + "/fmu/in/vehicle_command";
        std::string status_topic = ns + "/fmu/out/vehicle_status";
        std::string local_pos_topic = ns + "/fmu/out/vehicle_local_position";
        std::string traj_upload_topic = ns + "/trajectory_upload";

        RCLCPP_INFO(this->get_logger(), "Publishing to:");
        RCLCPP_INFO(this->get_logger(), "  %s", offboard_topic.c_str());
        RCLCPP_INFO(this->get_logger(), "  %s", trajectory_topic.c_str());
        RCLCPP_INFO(this->get_logger(), "  %s", vehicle_cmd_topic.c_str());
        RCLCPP_INFO(this->get_logger(), "Subscribing to:");
        RCLCPP_INFO(this->get_logger(), "  %s", status_topic.c_str());
        RCLCPP_INFO(this->get_logger(), "  %s", local_pos_topic.c_str());
        RCLCPP_INFO(this->get_logger(), "  %s", traj_upload_topic.c_str());

        offboard_control_mode_pub_ = this->create_publisher<px4_msgs::msg::OffboardControlMode>(offboard_topic, 10);
        trajectory_setpoint_pub_ = this->create_publisher<px4_msgs::msg::TrajectorySetpoint>(trajectory_topic, 10);
        vehicle_command_pub_ = this->create_publisher<px4_msgs::msg::VehicleCommand>(vehicle_cmd_topic, 10);
        capability_profile_pub_ = this->create_publisher<robot_control_interfaces::msg::CapabilityProfile>(
            "/orchestrator/capability_profile", 10);
        robot_state_pub_ = this->create_publisher<robot_control_interfaces::msg::RobotState>(
            "/orchestrator/robot_state", 10);
        task_ack_pub_ = this->create_publisher<robot_control_interfaces::msg::TaskAck>(
            "/orchestrator/task_ack", 10);
        task_update_pub_ = this->create_publisher<robot_control_interfaces::msg::TaskUpdate>(
            "/orchestrator/task_update", 10);

        rclcpp::QoS qos_profile{rclcpp::SensorDataQoS()};

        vehicle_status_sub_ = this->create_subscription<px4_msgs::msg::VehicleStatus>(
            status_topic, qos_profile,
            std::bind(&UavManager::vehicle_status_callback, this, std::placeholders::_1));

        local_position_sub_ = this->create_subscription<px4_msgs::msg::VehicleLocalPosition>(
            local_pos_topic, qos_profile,
            std::bind(&UavManager::local_position_callback, this, std::placeholders::_1));

        trajectory_sub_ = this->create_subscription<geometry_msgs::msg::PoseArray>(
            traj_upload_topic, 10, std::bind(&UavManager::trajectory_callback, this, std::placeholders::_1));

        task_command_sub_ = this->create_subscription<robot_control_interfaces::msg::TaskCommand>(
            "/orchestrator/task_command", 10, std::bind(&UavManager::task_command_callback, this, std::placeholders::_1));

        timer_ = this->create_wall_timer(50ms, std::bind(&UavManager::control_loop, this));
        robot_state_timer_ = this->create_wall_timer(1s, std::bind(&UavManager::publish_robot_state, this));
        capability_profile_timer_ =
            this->create_wall_timer(2s, std::bind(&UavManager::publish_capability_profile, this));

        publish_capability_profile();
    }

private:
    int drone_id_{};
    std::string robot_id_;
    std::string assets_file_;
    std::string sectors_file_;
    rclcpp::TimerBase::SharedPtr timer_;
    rclcpp::TimerBase::SharedPtr robot_state_timer_;
    rclcpp::TimerBase::SharedPtr capability_profile_timer_;

    rclcpp::Publisher<px4_msgs::msg::OffboardControlMode>::SharedPtr offboard_control_mode_pub_;
    rclcpp::Publisher<px4_msgs::msg::TrajectorySetpoint>::SharedPtr trajectory_setpoint_pub_;
    rclcpp::Publisher<px4_msgs::msg::VehicleCommand>::SharedPtr vehicle_command_pub_;
    rclcpp::Publisher<robot_control_interfaces::msg::CapabilityProfile>::SharedPtr capability_profile_pub_;
    rclcpp::Publisher<robot_control_interfaces::msg::RobotState>::SharedPtr robot_state_pub_;
    rclcpp::Publisher<robot_control_interfaces::msg::TaskAck>::SharedPtr task_ack_pub_;
    rclcpp::Publisher<robot_control_interfaces::msg::TaskUpdate>::SharedPtr task_update_pub_;

    rclcpp::Subscription<px4_msgs::msg::VehicleStatus>::SharedPtr vehicle_status_sub_;
    rclcpp::Subscription<px4_msgs::msg::VehicleLocalPosition>::SharedPtr local_position_sub_;
    rclcpp::Subscription<geometry_msgs::msg::PoseArray>::SharedPtr trajectory_sub_;
    rclcpp::Subscription<robot_control_interfaces::msg::TaskCommand>::SharedPtr task_command_sub_;

    FlightState current_state_ = FlightState::WAITING;
    std::vector<std::array<float, 3>> waypoints_;
    uint64_t waypoint_index_ = 0;
    bool armed_ = false;
    bool waypoint_reached_ = false;
    uint64_t offboard_setpoint_counter_ = 0;
    std::array<float, 3> next_waypoint_ = {0.0f, 0.0f, -8.0f};
    int32_t heartbeat_counter_ = 0;
    float posX_ = 0.0f;
    float posY_ = 0.0f;
    float posZ_ = 0.0f;
    float velocity_mps_ = 0.0f;
    float last_progress_pct_ = -1.0f;
    const float waypoint_accuracy_ = 0.5f;
    const std::chrono::seconds pending_command_timeout_{5};

    std::optional<TaskContext> pending_task_context_;
    std::optional<TaskContext> active_task_context_;
    std::optional<rclcpp::Time> pending_task_received_at_;
    std::unordered_map<std::string, std::vector<std::string>> sector_assets_;
    std::unordered_map<std::string, std::string> asset_notes_;

    void load_anomaly_config()
    {
        sector_assets_.clear();
        asset_notes_.clear();

        try {
            const auto assets_yaml = YAML::LoadFile(assets_file_);
            const auto assets_node = assets_yaml["assets"];
            if (assets_node && assets_node.IsSequence()) {
                for (const auto &asset_node : assets_node) {
                    const auto asset_id = asset_node["asset_id"].as<std::string>();
                    if (asset_node["notes"]) {
                        asset_notes_[asset_id] = asset_node["notes"].as<std::string>();
                    }
                }
            }

            const auto sectors_yaml = YAML::LoadFile(sectors_file_);
            const auto sectors_node = sectors_yaml["sectors"];
            if (sectors_node && sectors_node.IsSequence()) {
                for (const auto &sector_node : sectors_node) {
                    const auto sector_id = sector_node["sector_id"].as<std::string>();
                    auto &assets = sector_assets_[sector_id];
                    const auto sector_assets_node = sector_node["assets"];
                    if (!sector_assets_node || !sector_assets_node.IsSequence()) {
                        continue;
                    }
                    for (const auto &asset_id_node : sector_assets_node) {
                        assets.push_back(asset_id_node.as<std::string>());
                    }
                }
            }

            RCLCPP_INFO(
                this->get_logger(),
                "Loaded anomaly config from %s and %s",
                assets_file_.c_str(),
                sectors_file_.c_str());
        } catch (const std::exception &ex) {
            RCLCPP_WARN(
                this->get_logger(),
                "Failed to load anomaly config: %s",
                ex.what());
        }
    }

    bool is_busy() const
    {
        return pending_task_context_.has_value() || active_task_context_.has_value() ||
               current_state_ != FlightState::WAITING || !waypoints_.empty();
    }

    void publish_capability_profile()
    {
        robot_control_interfaces::msg::CapabilityProfile msg;
        msg.robot_id = robot_id_;
        msg.platform = robot_control_interfaces::msg::CapabilityProfile::PLATFORM_UAV;
        msg.max_speed_mps = 15.0f;
        msg.max_run_time_s = 1800.0f;
        msg.sensors = {"RGB", "THERMAL"};
        msg.task_types_supported = {
            robot_control_interfaces::msg::CapabilityProfile::TASK_INSPECT,
            robot_control_interfaces::msg::CapabilityProfile::TASK_VERIFY,
            robot_control_interfaces::msg::CapabilityProfile::TASK_PATROL,
            robot_control_interfaces::msg::CapabilityProfile::TASK_RETURN_HOME};
        capability_profile_pub_->publish(msg);
    }

    void publish_robot_state()
    {
        robot_control_interfaces::msg::RobotState msg;
        msg.robot_id = robot_id_;
        msg.mission_id = active_task_context_ ? active_task_context_->mission_id
                        : pending_task_context_ ? pending_task_context_->mission_id
                                                : "";
        msg.current_task_id = active_task_context_ ? active_task_context_->task_id
                             : pending_task_context_ ? pending_task_context_->task_id
                                                     : "";
        msg.x_m = posX_;
        msg.y_m = posY_;
        msg.yaw_rad = 0.0f;
        msg.z_m = posZ_;
        msg.velocity_mps = velocity_mps_;
        msg.battery_pct = 100.0f;
        msg.health_status = robot_control_interfaces::msg::RobotState::HEALTH_OK;
        msg.faults = {};
        msg.availability_status =
            is_busy()
                ? robot_control_interfaces::msg::RobotState::AVAIL_BUSY
                : robot_control_interfaces::msg::RobotState::AVAIL_IDLE;
        msg.heartbeat = heartbeat_counter_++;
        robot_state_pub_->publish(msg);
    }

    void publish_task_ack(
        const TaskContext &context,
        uint8_t decision,
        uint8_t reject_reason_code = robot_control_interfaces::msg::TaskAck::REASON_NONE,
        const std::string &reject_reason_detail = "")
    {
        robot_control_interfaces::msg::TaskAck msg;
        msg.mission_id = context.mission_id;
        msg.robot_id = robot_id_;
        msg.task_id = context.task_id;
        msg.command_id = context.command_id;
        msg.decision = decision;
        msg.reject_reason_code = reject_reason_code;
        msg.reject_reason_detail = reject_reason_detail;
        task_ack_pub_->publish(msg);
    }

    void publish_task_update(
        const TaskContext &context,
        uint8_t status,
        float progress_pct,
        const std::string &detail)
    {
        robot_control_interfaces::msg::TaskUpdate msg;
        msg.mission_id = context.mission_id;
        msg.robot_id = robot_id_;
        msg.task_id = context.task_id;
        msg.status = status;
        msg.progress_pct = progress_pct;
        msg.status_detail = detail;
        msg.timestamp = iso_timestamp_now();
        task_update_pub_->publish(msg);
    }

    std::string build_anomaly_report(const TaskContext &context) const
    {
        std::vector<std::string> findings;

        if (!context.sector_id.empty()) {
            const auto sector_it = sector_assets_.find(context.sector_id);
            if (sector_it != sector_assets_.end()) {
                for (const auto &asset_id : sector_it->second) {
                    const auto note_it = asset_notes_.find(asset_id);
                    if (note_it != asset_notes_.end() && !note_it->second.empty()) {
                        findings.push_back(asset_id + ": " + note_it->second);
                    }
                }
            }
        }

        if (findings.empty() && !context.asset_id.empty()) {
            const auto note_it = asset_notes_.find(context.asset_id);
            if (note_it != asset_notes_.end() && !note_it->second.empty()) {
                findings.push_back(context.asset_id + ": " + note_it->second);
            }
        }

        if (findings.empty()) {
            return "No configured anomalies reported.";
        }

        std::ostringstream oss;
        oss << "Configured anomalies detected: ";
        for (std::size_t i = 0; i < findings.size(); ++i) {
            if (i > 0) {
                oss << "; ";
            }
            oss << findings[i];
        }
        return oss.str();
    }

    void maybe_expire_pending_command()
    {
        if (!pending_task_context_ || !pending_task_received_at_ || active_task_context_) {
            return;
        }

        if ((this->now() - *pending_task_received_at_).seconds() <= pending_command_timeout_.count()) {
            return;
        }

        publish_task_ack(
            *pending_task_context_,
            robot_control_interfaces::msg::TaskAck::REJECTED,
            robot_control_interfaces::msg::TaskAck::REASON_TARGET_INVALID,
            "No executable trajectory was received for this command.");
        pending_task_context_.reset();
        pending_task_received_at_.reset();
    }

    void task_command_callback(const robot_control_interfaces::msg::TaskCommand::SharedPtr msg)
    {
        if (msg->robot_id != robot_id_ || msg->type != robot_control_interfaces::msg::TaskCommand::ASSIGN) {
            return;
        }

        const auto context = TaskContext::from_command(*msg);

        if (is_busy()) {
            publish_task_ack(
                context,
                robot_control_interfaces::msg::TaskAck::REJECTED,
                robot_control_interfaces::msg::TaskAck::REASON_BUSY,
                "Robot is already executing another task.");
            return;
        }

        pending_task_context_ = context;
        pending_task_received_at_ = this->now();

        RCLCPP_INFO(
            this->get_logger(),
            "Buffered task command %s for mission %s",
            context.task_id.c_str(),
            context.mission_id.c_str());
    }

    void trajectory_callback(const geometry_msgs::msg::PoseArray::SharedPtr msg)
    {
        waypoints_.clear();
        for (const auto &pose : msg->poses) {
            std::array<float, 3> waypoint = {
                static_cast<float>(pose.position.x),
                static_cast<float>(pose.position.y),
                static_cast<float>(pose.position.z)};
            waypoints_.push_back(waypoint);
        }

        if (waypoints_.empty()) {
            RCLCPP_WARN(this->get_logger(), "Received empty trajectory");
            return;
        }

        if (pending_task_context_) {
            active_task_context_ = pending_task_context_;
            pending_task_context_.reset();
            pending_task_received_at_.reset();
            publish_task_ack(*active_task_context_, robot_control_interfaces::msg::TaskAck::ACCEPTED);
            publish_task_update(
                *active_task_context_,
                robot_control_interfaces::msg::TaskUpdate::STATUS_IN_PROGRESS,
                0.0f,
                "Trajectory accepted; taking off.");
        } else {
            RCLCPP_WARN(
                this->get_logger(),
                "Received trajectory without buffered task metadata. Progress feedback will be limited.");
        }

        waypoint_index_ = 0;
        offboard_setpoint_counter_ = 0;
        last_progress_pct_ = 0.0f;
        next_waypoint_ = {posX_, posY_, waypoints_.front()[2]};
        current_state_ = FlightState::TAKING_OFF;

        RCLCPP_INFO(this->get_logger(), "Received trajectory with %zu waypoints", waypoints_.size());
    }

    void publish_offboard_control_mode()
    {
        px4_msgs::msg::OffboardControlMode msg;
        msg.position = true;
        msg.timestamp = this->get_clock()->now().nanoseconds() / 1000;
        offboard_control_mode_pub_->publish(msg);
    }

    void publish_trajectory_setpoint(const std::array<float, 3> &position)
    {
        px4_msgs::msg::TrajectorySetpoint msg;
        msg.position = position;
        msg.timestamp = this->get_clock()->now().nanoseconds() / 1000;
        trajectory_setpoint_pub_->publish(msg);
    }

    void publish_vehicle_command(uint16_t command, float param1, float param2)
    {
        px4_msgs::msg::VehicleCommand msg;
        msg.param1 = param1;
        msg.param2 = param2;
        msg.command = command;
        msg.target_system = drone_id_ + 1;
        msg.target_component = 1;
        msg.source_system = 1;
        msg.source_component = 1;
        msg.from_external = true;
        msg.timestamp = this->get_clock()->now().nanoseconds() / 1000;
        vehicle_command_pub_->publish(msg);
    }

    void arm() { publish_vehicle_command(400, 1.0f, 0.0f); }
    void set_offboard_mode() { publish_vehicle_command(176, 1.0f, 6.0f); }

    void vehicle_status_callback(const px4_msgs::msg::VehicleStatus::SharedPtr msg)
    {
        armed_ = (msg->arming_state == msg->ARMING_STATE_ARMED);
    }

    void local_position_callback(const px4_msgs::msg::VehicleLocalPosition::SharedPtr msg)
    {
        velocity_mps_ = std::sqrt(msg->vx * msg->vx + msg->vy * msg->vy + msg->vz * msg->vz);
        posX_ = msg->x;
        posY_ = msg->y;
        posZ_ = msg->z;
        const float dx = posX_ - next_waypoint_[0];
        const float dy = posY_ - next_waypoint_[1];
        const float dz = posZ_ - next_waypoint_[2];
        waypoint_reached_ = (dx * dx + dy * dy + dz * dz) < (waypoint_accuracy_ * waypoint_accuracy_);
    }

    void publish_waypoint_progress()
    {
        if (!active_task_context_ || waypoints_.empty()) {
            return;
        }

        const auto completed_waypoints = static_cast<float>(waypoint_index_);
        const auto total_waypoints = static_cast<float>(waypoints_.size());
        const auto progress_pct = std::min(100.0f, (completed_waypoints / total_waypoints) * 100.0f);
        if (progress_pct <= last_progress_pct_) {
            return;
        }

        last_progress_pct_ = progress_pct;
        std::ostringstream detail;
        detail << "Reached waypoint " << waypoint_index_ << " of " << waypoints_.size() << ".";
        publish_task_update(
            *active_task_context_,
            robot_control_interfaces::msg::TaskUpdate::STATUS_IN_PROGRESS,
            progress_pct,
            detail.str());
    }

    void complete_active_task()
    {
        if (active_task_context_) {
            std::string detail = "Task completed.";
            if (active_task_context_->task_type == robot_control_interfaces::msg::TaskSpec::PATROL) {
                detail = "Patrol complete. " + build_anomaly_report(*active_task_context_);
            }

            publish_task_update(
                *active_task_context_,
                robot_control_interfaces::msg::TaskUpdate::STATUS_COMPLETED,
                100.0f,
                detail);
        }

        active_task_context_.reset();
        waypoints_.clear();
        waypoint_index_ = 0;
        offboard_setpoint_counter_ = 0;
        last_progress_pct_ = -1.0f;
        current_state_ = FlightState::WAITING;
    }

    void control_loop()
    {
        maybe_expire_pending_command();
        publish_offboard_control_mode();

        switch (current_state_) {
        case FlightState::WAITING:
            RCLCPP_INFO_ONCE(this->get_logger(), "State: WAITING");
            if (armed_) {
                publish_trajectory_setpoint(next_waypoint_);
            }
            break;

        case FlightState::TAKING_OFF:
            RCLCPP_INFO_ONCE(this->get_logger(), "State: TAKING_OFF");
            publish_trajectory_setpoint(next_waypoint_);
            if (++offboard_setpoint_counter_ == 10) {
                set_offboard_mode();
                arm();
            }

            if (waypoint_reached_) {
                current_state_ = FlightState::HOVERING;
                offboard_setpoint_counter_ = 0;
            }
            break;

        case FlightState::HOVERING:
            RCLCPP_INFO(this->get_logger(), "State: HOVERING");
            current_state_ = FlightState::FOLLOWING_TRAJECTORY;
            break;

        case FlightState::FOLLOWING_TRAJECTORY:
            RCLCPP_INFO_ONCE(this->get_logger(), "State: FOLLOWING_TRAJECTORY");
            if (waypoint_index_ >= waypoints_.size()) {
                complete_active_task();
                break;
            }

            next_waypoint_ = waypoints_[waypoint_index_];
            publish_trajectory_setpoint(next_waypoint_);
            if (waypoint_reached_) {
                RCLCPP_INFO(
                    this->get_logger(),
                    "Reached waypoint %lu: (%.2f, %.2f, %.2f)",
                    waypoint_index_,
                    next_waypoint_[0],
                    next_waypoint_[1],
                    next_waypoint_[2]);

                ++waypoint_index_;
                publish_waypoint_progress();
            }
            break;
        }
    }
};

int main(int argc, char *argv[])
{
    rclcpp::init(argc, argv);
    rclcpp::spin(std::make_shared<UavManager>());
    rclcpp::shutdown();
    return 0;
}
