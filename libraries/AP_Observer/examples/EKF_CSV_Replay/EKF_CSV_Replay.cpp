#define AP_OBSERVER_REPLAY_TEST 1

#include <AP_HAL/AP_HAL.h>
#include <AP_Observer/AP_Observer.h>
#include <stdio.h>
#include <stdlib.h>
#include <iostream>
#include <fstream>
#include <sstream>
#include <vector>
#include <string>
#include <new>
#include <cctype>
#include <cstring>
#include <unistd.h>

const AP_HAL::HAL& hal = AP_HAL::get_HAL();

void setup();
void loop();

AP_Observer observer;

struct ReplayData {
    uint32_t time_us;
    float plx;
    float ply;
    float plz;
    int sw;
    float real_freq;
    float real_phase;
};

struct ReplayRunConfig;
static std::vector<ReplayData> read_csv(const char* filename, bool& has_extended_columns);
static void run_case(const char* out_filename, const std::vector<ReplayData>& data, bool force_window, const ReplayRunConfig& cfg);

static bool ends_with_ignore_case(const std::string& value, const std::string& suffix) {
    if (value.size() < suffix.size()) {
        return false;
    }
    const size_t offset = value.size() - suffix.size();
    for (size_t i = 0; i < suffix.size(); i++) {
        if (std::tolower(static_cast<unsigned char>(value[offset + i])) !=
            std::tolower(static_cast<unsigned char>(suffix[i]))) {
            return false;
        }
    }
    return true;
}

static std::string basename_without_ext(const std::string& path) {
    std::string base = path;
    const size_t lastslash = base.find_last_of("/");
    if (lastslash != std::string::npos) {
        base = base.substr(lastslash + 1);
    }
    const size_t dot = base.find_last_of('.');
    if (dot != std::string::npos) {
        base = base.substr(0, dot);
    }
    return base;
}

static std::string shell_quote(const std::string& input) {
    std::string out;
    out.reserve(input.size() + 2);
    out.push_back('\'');
    for (const char c : input) {
        if (c == '\'') {
            out += "'\\''";
        } else {
            out.push_back(c);
        }
    }
    out.push_back('\'');
    return out;
}

static bool convert_bin_to_csv(const std::string& bin_path, const std::string& csv_path) {
    const char* script_path = "analysis/replay/bin_to_replay_csv.py";
    const char* venv_python = "venv/bin/python3";
    const char* python_cmd = (access(venv_python, X_OK) == 0) ? venv_python : "python3";

    const std::string command =
        std::string(python_cmd) + " " + shell_quote(script_path) +
        " --input " + shell_quote(bin_path) +
        " --output " + shell_quote(csv_path);

    printf("Converting BIN -> CSV: %s\n", bin_path.c_str());
    const int rc = system(command.c_str());
    if (rc != 0) {
        printf("BIN conversion failed (rc=%d): %s\n", rc, command.c_str());
        return false;
    }
    return true;
}

static bool generate_plots_from_result(const std::string& result_csv,
                                       const std::string& plot_dir,
                                       const std::string& title) {
    const char* script_path = "analysis/replay/plot_replay_results.py";
    const char* venv_python = "venv/bin/python3";
    const char* python_cmd = (access(venv_python, X_OK) == 0) ? venv_python : "python3";

    const std::string command =
        std::string(python_cmd) + " " + shell_quote(script_path) +
        " --input " + shell_quote(result_csv) +
        " --outdir " + shell_quote(plot_dir) +
        " --title " + shell_quote(title);

    printf("Generating replay plots: %s\n", result_csv.c_str());
    const int rc = system(command.c_str());
    if (rc != 0) {
        printf("Plot generation failed (rc=%d): %s\n", rc, command.c_str());
        return false;
    }
    return true;
}

static bool ensure_directory(const std::string& path) {
    const std::string command = "mkdir -p " + shell_quote(path);
    const int rc = system(command.c_str());
    return rc == 0;
}

struct ReplayRunConfig {
    bool single_mode = false;
    bool generate_plots = false;
    bool force_window_override = false;
    std::string input_path;
    std::string output_dir;
    std::string tag;
    std::string sw_mode = "always-on";
    bool has_ekf_w_init_hz = false;
    float ekf_w_init_hz = 0.0f;
    bool has_ekf_q_w = false;
    float ekf_q_w = 0.0f;
    bool has_ekf_q_d = false;
    float ekf_q_d = 0.0f;
    bool has_ekf_q_dd = false;
    float ekf_q_dd = 0.0f;
    bool has_ekf_q_c = false;
    float ekf_q_c = 0.0f;
    bool has_ekf_r_meas = false;
    float ekf_r_meas = 0.0f;
    bool has_ekf_pred_time = false;
    float ekf_pred_time = 0.0f;
    bool has_ekf_axis_gate = false;
    int ekf_axis_gate = 1;
    bool has_ekf_amp_min = false;
    float ekf_amp_min = 0.08f;
    bool has_ekf_amp_max = false;
    float ekf_amp_max = 1.2f;
    bool has_ekf_innov_max = false;
    float ekf_innov_max = 0.7f;
    bool has_ekf_nis_max = false;
    float ekf_nis_max = 4.0f;
    bool has_ekf_energy_gate = false;
    int ekf_energy_gate = 1;
    bool has_ekf_energy_rms_on = false;
    float ekf_energy_rms_on = 0.20f;
    bool has_ekf_energy_rms_off = false;
    float ekf_energy_rms_off = 0.16f;
    bool has_ekf_energy_tau = false;
    float ekf_energy_tau = 2.0f;
    bool has_ekf_force_hold_max = false;
    float ekf_force_hold_max = 1.5f;
    bool has_ekf_force_reject_min = false;
    float ekf_force_reject_min = 5.0f;
    bool has_ekf_reset_on_switch = false;
    int ekf_reset_on_switch = 0;
    bool has_ekf_axis_mask = false;
    int ekf_axis_mask = 3;
    bool has_ekf_hold_omega_when_off = false;
    int ekf_hold_omega_when_off = 0;
    bool has_ekf_robust_update = false;
    int ekf_robust_update = 0;
    bool has_ekf_robust_nis_reject = false;
    float ekf_robust_nis_reject = 3.0f;
    bool has_ekf_sh_beta = false;
    float ekf_sh_beta = 0.0f;
};

static bool parse_replay_args(ReplayRunConfig& cfg) {
    uint8_t argc = 0;
    char * const *argv = nullptr;
    hal.util->commandline_arguments(argc, argv);

    if (argc <= 1) {
        return true;
    }

    for (uint8_t i = 1; i < argc; i++) {
        const char* arg = argv[i];
        if (strcmp(arg, "--help") == 0 || strcmp(arg, "-h") == 0) {
            printf("Usage:\n");
            printf("  ./build/sitl/examples/EKF_CSV_Replay\n");
            printf("  ./build/sitl/examples/EKF_CSV_Replay --input <path_to_csv_or_bin> [--outdir <dir>] [--tag <name>] [--plot] [--force-window]\n");
            printf("      [--ekf-w-init-hz <hz>] [--ekf-q-w <var>] [--ekf-q-d <var>] [--ekf-q-dd <var>] [--ekf-q-c <var>] [--ekf-r-meas <var>] [--ekf-pred-time <s>]\n");
            printf("      [--sw-mode log|always-on|always-off] [--ekf-reset-on-switch 0|1]\n");
            printf("      [--ekf-axis-gate 0|1] [--ekf-amp-min <v>] [--ekf-amp-max <v>] [--ekf-innov-max <v>] [--ekf-nis-max <v>]\n");
            printf("      [--ekf-energy-gate 0|1] [--ekf-energy-rms-on <v>] [--ekf-energy-rms-off <v>] [--ekf-energy-tau <s>]\n");
            printf("      [--ekf-force-hold-max <n>] [--ekf-force-reject-min <n>] [--ekf-axis-mask <mask>] [--ekf-hold-omega-off 0|1]\n");
            printf("      [--ekf-robust-update 0|1] [--ekf-robust-nis-reject <scale>]\n");
            printf("      [--ekf-sh-beta <0..1>]\n");
            printf("\n");
            printf("Default mode runs the built-in regression file list.\n");
            printf("Default SW mode is always-on for replay consistency.\n");
            exit(0);
        }

        const char* next = (i + 1 < argc) ? argv[i + 1] : nullptr;

        if ((strcmp(arg, "--input") == 0) && next != nullptr) {
            cfg.input_path = next;
            cfg.single_mode = true;
            i++;
            continue;
        }
        if (strncmp(arg, "--input=", 8) == 0) {
            cfg.input_path = std::string(arg + 8);
            cfg.single_mode = true;
            continue;
        }

        if ((strcmp(arg, "--outdir") == 0) && next != nullptr) {
            cfg.output_dir = next;
            i++;
            continue;
        }
        if (strncmp(arg, "--outdir=", 9) == 0) {
            cfg.output_dir = std::string(arg + 9);
            continue;
        }

        if ((strcmp(arg, "--tag") == 0) && next != nullptr) {
            cfg.tag = next;
            i++;
            continue;
        }
        if (strncmp(arg, "--tag=", 6) == 0) {
            cfg.tag = std::string(arg + 6);
            continue;
        }

        if (strcmp(arg, "--plot") == 0) {
            cfg.generate_plots = true;
            continue;
        }
        if (strcmp(arg, "--no-plot") == 0) {
            cfg.generate_plots = false;
            continue;
        }
        if (strcmp(arg, "--force-window") == 0) {
            cfg.force_window_override = true;
            continue;
        }

        if ((strcmp(arg, "--sw-mode") == 0) && next != nullptr) {
            cfg.sw_mode = next;
            i++;
            continue;
        }
        if (strncmp(arg, "--sw-mode=", 10) == 0) {
            cfg.sw_mode = std::string(arg + 10);
            continue;
        }

        if ((strcmp(arg, "--ekf-reset-on-switch") == 0) && next != nullptr) {
            cfg.ekf_reset_on_switch = (int)strtol(next, nullptr, 10);
            cfg.has_ekf_reset_on_switch = true;
            i++;
            continue;
        }
        if (strncmp(arg, "--ekf-reset-on-switch=", 22) == 0) {
            cfg.ekf_reset_on_switch = (int)strtol(arg + 22, nullptr, 10);
            cfg.has_ekf_reset_on_switch = true;
            continue;
        }

        if ((strcmp(arg, "--ekf-axis-mask") == 0) && next != nullptr) {
            cfg.ekf_axis_mask = (int)strtol(next, nullptr, 10);
            cfg.has_ekf_axis_mask = true;
            i++;
            continue;
        }
        if (strncmp(arg, "--ekf-axis-mask=", 16) == 0) {
            cfg.ekf_axis_mask = (int)strtol(arg + 16, nullptr, 10);
            cfg.has_ekf_axis_mask = true;
            continue;
        }

        if ((strcmp(arg, "--ekf-hold-omega-off") == 0) && next != nullptr) {
            cfg.ekf_hold_omega_when_off = (int)strtol(next, nullptr, 10);
            cfg.has_ekf_hold_omega_when_off = true;
            i++;
            continue;
        }
        if (strncmp(arg, "--ekf-hold-omega-off=", 21) == 0) {
            cfg.ekf_hold_omega_when_off = (int)strtol(arg + 21, nullptr, 10);
            cfg.has_ekf_hold_omega_when_off = true;
            continue;
        }

        if ((strcmp(arg, "--ekf-robust-update") == 0) && next != nullptr) {
            cfg.ekf_robust_update = (int)strtol(next, nullptr, 10);
            cfg.has_ekf_robust_update = true;
            i++;
            continue;
        }
        if (strncmp(arg, "--ekf-robust-update=", 20) == 0) {
            cfg.ekf_robust_update = (int)strtol(arg + 20, nullptr, 10);
            cfg.has_ekf_robust_update = true;
            continue;
        }

        if ((strcmp(arg, "--ekf-robust-nis-reject") == 0) && next != nullptr) {
            cfg.ekf_robust_nis_reject = strtof(next, nullptr);
            cfg.has_ekf_robust_nis_reject = true;
            i++;
            continue;
        }
        if (strncmp(arg, "--ekf-robust-nis-reject=", 24) == 0) {
            cfg.ekf_robust_nis_reject = strtof(arg + 24, nullptr);
            cfg.has_ekf_robust_nis_reject = true;
            continue;
        }

        if ((strcmp(arg, "--ekf-sh-beta") == 0) && next != nullptr) {
            cfg.ekf_sh_beta = strtof(next, nullptr);
            cfg.has_ekf_sh_beta = true;
            i++;
            continue;
        }
        if (strncmp(arg, "--ekf-sh-beta=", 14) == 0) {
            cfg.ekf_sh_beta = strtof(arg + 14, nullptr);
            cfg.has_ekf_sh_beta = true;
            continue;
        }

        if ((strcmp(arg, "--ekf-axis-gate") == 0) && next != nullptr) {
            cfg.ekf_axis_gate = (int)strtol(next, nullptr, 10);
            cfg.has_ekf_axis_gate = true;
            i++;
            continue;
        }
        if (strncmp(arg, "--ekf-axis-gate=", 16) == 0) {
            cfg.ekf_axis_gate = (int)strtol(arg + 16, nullptr, 10);
            cfg.has_ekf_axis_gate = true;
            continue;
        }

        if ((strcmp(arg, "--ekf-amp-min") == 0) && next != nullptr) {
            cfg.ekf_amp_min = strtof(next, nullptr);
            cfg.has_ekf_amp_min = true;
            i++;
            continue;
        }
        if (strncmp(arg, "--ekf-amp-min=", 14) == 0) {
            cfg.ekf_amp_min = strtof(arg + 14, nullptr);
            cfg.has_ekf_amp_min = true;
            continue;
        }

        if ((strcmp(arg, "--ekf-amp-max") == 0) && next != nullptr) {
            cfg.ekf_amp_max = strtof(next, nullptr);
            cfg.has_ekf_amp_max = true;
            i++;
            continue;
        }
        if (strncmp(arg, "--ekf-amp-max=", 14) == 0) {
            cfg.ekf_amp_max = strtof(arg + 14, nullptr);
            cfg.has_ekf_amp_max = true;
            continue;
        }

        if ((strcmp(arg, "--ekf-innov-max") == 0) && next != nullptr) {
            cfg.ekf_innov_max = strtof(next, nullptr);
            cfg.has_ekf_innov_max = true;
            i++;
            continue;
        }
        if (strncmp(arg, "--ekf-innov-max=", 16) == 0) {
            cfg.ekf_innov_max = strtof(arg + 16, nullptr);
            cfg.has_ekf_innov_max = true;
            continue;
        }

        if ((strcmp(arg, "--ekf-nis-max") == 0) && next != nullptr) {
            cfg.ekf_nis_max = strtof(next, nullptr);
            cfg.has_ekf_nis_max = true;
            i++;
            continue;
        }
        if (strncmp(arg, "--ekf-nis-max=", 14) == 0) {
            cfg.ekf_nis_max = strtof(arg + 14, nullptr);
            cfg.has_ekf_nis_max = true;
            continue;
        }

        if ((strcmp(arg, "--ekf-energy-gate") == 0) && next != nullptr) {
            cfg.ekf_energy_gate = (int)strtol(next, nullptr, 10);
            cfg.has_ekf_energy_gate = true;
            i++;
            continue;
        }
        if (strncmp(arg, "--ekf-energy-gate=", 18) == 0) {
            cfg.ekf_energy_gate = (int)strtol(arg + 18, nullptr, 10);
            cfg.has_ekf_energy_gate = true;
            continue;
        }

        if ((strcmp(arg, "--ekf-energy-rms-on") == 0) && next != nullptr) {
            cfg.ekf_energy_rms_on = strtof(next, nullptr);
            cfg.has_ekf_energy_rms_on = true;
            i++;
            continue;
        }
        if (strncmp(arg, "--ekf-energy-rms-on=", 20) == 0) {
            cfg.ekf_energy_rms_on = strtof(arg + 20, nullptr);
            cfg.has_ekf_energy_rms_on = true;
            continue;
        }

        if ((strcmp(arg, "--ekf-energy-rms-off") == 0) && next != nullptr) {
            cfg.ekf_energy_rms_off = strtof(next, nullptr);
            cfg.has_ekf_energy_rms_off = true;
            i++;
            continue;
        }
        if (strncmp(arg, "--ekf-energy-rms-off=", 21) == 0) {
            cfg.ekf_energy_rms_off = strtof(arg + 21, nullptr);
            cfg.has_ekf_energy_rms_off = true;
            continue;
        }

        if ((strcmp(arg, "--ekf-energy-tau") == 0) && next != nullptr) {
            cfg.ekf_energy_tau = strtof(next, nullptr);
            cfg.has_ekf_energy_tau = true;
            i++;
            continue;
        }
        if (strncmp(arg, "--ekf-energy-tau=", 17) == 0) {
            cfg.ekf_energy_tau = strtof(arg + 17, nullptr);
            cfg.has_ekf_energy_tau = true;
            continue;
        }

        if ((strcmp(arg, "--ekf-force-hold-max") == 0) && next != nullptr) {
            cfg.ekf_force_hold_max = strtof(next, nullptr);
            cfg.has_ekf_force_hold_max = true;
            i++;
            continue;
        }
        if (strncmp(arg, "--ekf-force-hold-max=", 21) == 0) {
            cfg.ekf_force_hold_max = strtof(arg + 21, nullptr);
            cfg.has_ekf_force_hold_max = true;
            continue;
        }

        if ((strcmp(arg, "--ekf-force-reject-min") == 0) && next != nullptr) {
            cfg.ekf_force_reject_min = strtof(next, nullptr);
            cfg.has_ekf_force_reject_min = true;
            i++;
            continue;
        }
        if (strncmp(arg, "--ekf-force-reject-min=", 23) == 0) {
            cfg.ekf_force_reject_min = strtof(arg + 23, nullptr);
            cfg.has_ekf_force_reject_min = true;
            continue;
        }

        if ((strcmp(arg, "--ekf-w-init-hz") == 0) && next != nullptr) {
            cfg.ekf_w_init_hz = strtof(next, nullptr);
            cfg.has_ekf_w_init_hz = true;
            i++;
            continue;
        }
        if (strncmp(arg, "--ekf-w-init-hz=", 16) == 0) {
            cfg.ekf_w_init_hz = strtof(arg + 16, nullptr);
            cfg.has_ekf_w_init_hz = true;
            continue;
        }

        if ((strcmp(arg, "--ekf-q-w") == 0) && next != nullptr) {
            cfg.ekf_q_w = strtof(next, nullptr);
            cfg.has_ekf_q_w = true;
            i++;
            continue;
        }
        if (strncmp(arg, "--ekf-q-w=", 10) == 0) {
            cfg.ekf_q_w = strtof(arg + 10, nullptr);
            cfg.has_ekf_q_w = true;
            continue;
        }

        if ((strcmp(arg, "--ekf-q-d") == 0) && next != nullptr) {
            cfg.ekf_q_d = strtof(next, nullptr);
            cfg.has_ekf_q_d = true;
            i++;
            continue;
        }
        if (strncmp(arg, "--ekf-q-d=", 10) == 0) {
            cfg.ekf_q_d = strtof(arg + 10, nullptr);
            cfg.has_ekf_q_d = true;
            continue;
        }

        if ((strcmp(arg, "--ekf-q-dd") == 0) && next != nullptr) {
            cfg.ekf_q_dd = strtof(next, nullptr);
            cfg.has_ekf_q_dd = true;
            i++;
            continue;
        }
        if (strncmp(arg, "--ekf-q-dd=", 11) == 0) {
            cfg.ekf_q_dd = strtof(arg + 11, nullptr);
            cfg.has_ekf_q_dd = true;
            continue;
        }

        if ((strcmp(arg, "--ekf-q-c") == 0) && next != nullptr) {
            cfg.ekf_q_c = strtof(next, nullptr);
            cfg.has_ekf_q_c = true;
            i++;
            continue;
        }
        if (strncmp(arg, "--ekf-q-c=", 10) == 0) {
            cfg.ekf_q_c = strtof(arg + 10, nullptr);
            cfg.has_ekf_q_c = true;
            continue;
        }

        if ((strcmp(arg, "--ekf-r-meas") == 0) && next != nullptr) {
            cfg.ekf_r_meas = strtof(next, nullptr);
            cfg.has_ekf_r_meas = true;
            i++;
            continue;
        }
        if (strncmp(arg, "--ekf-r-meas=", 13) == 0) {
            cfg.ekf_r_meas = strtof(arg + 13, nullptr);
            cfg.has_ekf_r_meas = true;
            continue;
        }

        if ((strcmp(arg, "--ekf-pred-time") == 0) && next != nullptr) {
            cfg.ekf_pred_time = strtof(next, nullptr);
            cfg.has_ekf_pred_time = true;
            i++;
            continue;
        }
        if (strncmp(arg, "--ekf-pred-time=", 16) == 0) {
            cfg.ekf_pred_time = strtof(arg + 16, nullptr);
            cfg.has_ekf_pred_time = true;
            continue;
        }

        printf("Unknown argument: %s\n", arg);
        return false;
    }

    if (cfg.single_mode && cfg.input_path.empty()) {
        printf("--input is required for single-input mode.\n");
        return false;
    }

    if (cfg.sw_mode != "log" && cfg.sw_mode != "always-on" && cfg.sw_mode != "always-off") {
        printf("--sw-mode must be one of: log, always-on, always-off\n");
        return false;
    }

    return true;
}

static bool run_single_input_case(const ReplayRunConfig& cfg) {
    std::string input_path = cfg.input_path;
    const std::string input_base = basename_without_ext(input_path);
    std::string output_base = cfg.tag.empty() ? input_base : cfg.tag;

    std::string output_dir = cfg.output_dir;
    if (output_dir.empty()) {
        output_dir = "analysis/replay/results/runs/" + output_base;
    }
    const std::string plot_dir = output_dir + "/plots";
    if (!ensure_directory(plot_dir)) {
        printf("Failed to create output directories: %s\n", output_dir.c_str());
        return false;
    }

    std::string csv_path = input_path;
    if (ends_with_ignore_case(input_path, ".bin")) {
        csv_path = output_dir + "/" + input_base + "_from_bin.csv";
        if (!convert_bin_to_csv(input_path, csv_path)) {
            return false;
        }
        if (cfg.tag.empty()) {
            output_base = input_base + "_bin";
        }
    }

    bool has_extended_columns = false;
    std::vector<ReplayData> data = read_csv(csv_path.c_str(), has_extended_columns);
    if (data.empty()) {
        printf("Failed to read CSV: %s\n", csv_path.c_str());
        return false;
    }
    printf("Read %lu records from %s.\n", data.size(), csv_path.c_str());

    bool force_window = (input_base == "00000434") && has_extended_columns;
    if (cfg.force_window_override) {
        force_window = true;
    }

    const std::string result_csv = output_dir + "/" + output_base + "_result.csv";
    printf("Running %s (%s)...\n", output_base.c_str(), force_window ? "windowed" : "standard");
    run_case(result_csv.c_str(), data, force_window, cfg);

    if (cfg.generate_plots) {
        generate_plots_from_result(result_csv, plot_dir, output_base);
    }
    return true;
}

static std::vector<ReplayData> read_csv(const char* filename, bool& has_extended_columns) {
    std::vector<ReplayData> data;
    has_extended_columns = true;
    std::ifstream file(filename);
    std::string line;
    
    // Skip header
    std::getline(file, line);
    
    while (std::getline(file, line)) {
        if (line.empty()) continue;
        std::stringstream ss(line);
        std::string item;
        ReplayData d;
        d.time_us = 0;
        d.plx = 0.0f;
        d.ply = 0.0f;
        d.plz = 0.0f;
        d.sw = 0;
        d.real_freq = 0.0f;
        d.real_phase = 0.0f;
        uint8_t fields = 0;
        
        if (std::getline(ss, item, ',')) { d.time_us = strtoul(item.c_str(), nullptr, 10); fields++; }
        if (std::getline(ss, item, ',')) { d.plx = strtof(item.c_str(), nullptr); fields++; }
        if (std::getline(ss, item, ',')) { d.ply = strtof(item.c_str(), nullptr); fields++; }
        if (std::getline(ss, item, ',')) { d.plz = strtof(item.c_str(), nullptr); fields++; }
        if (std::getline(ss, item, ',')) { d.sw = strtol(item.c_str(), nullptr, 10); fields++; }
        if (std::getline(ss, item, ',')) { d.real_freq = strtof(item.c_str(), nullptr); fields++; }
        if (std::getline(ss, item, ',')) { d.real_phase = strtof(item.c_str(), nullptr); fields++; }

        if (fields < 7) {
            has_extended_columns = false;
        }
        data.push_back(d);
    }
    return data;
}

static void run_case(const char* out_filename, const std::vector<ReplayData>& data, bool force_window, const ReplayRunConfig& cfg) {
    // Reset observer by reconstruction
    new (&observer) AP_Observer();
    observer.set_replay_time_ms(0); // Ensure time starts at 0 for init
    observer.init();
    // 初期化後にパラメータを上書き
    observer.set_params_for_replay(0.5794f, 20.0f, 0.0f);
    
    observer.set_ekf_process_noises_for_replay(
        cfg.has_ekf_q_d ? cfg.ekf_q_d : 9.5367432e-12f,
        cfg.has_ekf_q_dd ? cfg.ekf_q_dd : 2.3841858e-11f,
        cfg.has_ekf_q_c ? cfg.ekf_q_c : 4.7683716e-13f
    );
    observer.set_ekf_q_w_for_replay(cfg.has_ekf_q_w ? cfg.ekf_q_w : 0.0005f);
    observer.set_ekf_r_meas_for_replay(cfg.has_ekf_r_meas ? cfg.ekf_r_meas : 46.0f);

    // Keep replay behavior deterministic and aligned with historical baseline unless CLI overrides are added.
    observer.set_ekf_shared_blend_beta_for_replay(cfg.has_ekf_sh_beta ? cfg.ekf_sh_beta : 0.0f);
    observer.set_ekf_axis_mask_for_replay((uint8_t)MAX(0, cfg.has_ekf_axis_mask ? cfg.ekf_axis_mask : 3));
    observer.set_ekf_energy_gate_for_replay(
        cfg.has_ekf_energy_gate ? (cfg.ekf_energy_gate != 0) : true,
        cfg.has_ekf_energy_rms_on ? cfg.ekf_energy_rms_on : 0.20f,
        cfg.has_ekf_energy_rms_off ? cfg.ekf_energy_rms_off : 0.16f,
        cfg.has_ekf_energy_tau ? cfg.ekf_energy_tau : 2.0f
    );
    observer.set_ekf_innovation_limits_for_replay(
        cfg.has_ekf_innov_max ? cfg.ekf_innov_max : 0.7f,
        cfg.has_ekf_nis_max ? cfg.ekf_nis_max : 4.0f
    );
    observer.set_ekf_force_thresholds_for_replay(
        cfg.has_ekf_force_hold_max ? cfg.ekf_force_hold_max : 0.10f,
        cfg.has_ekf_force_reject_min ? cfg.ekf_force_reject_min : 5.0f
    );
    observer.set_ekf_robust_update_for_replay(
        cfg.has_ekf_robust_update ? (cfg.ekf_robust_update != 0) : false,
        cfg.has_ekf_robust_nis_reject ? cfg.ekf_robust_nis_reject : 3.0f
    );
    if (cfg.has_ekf_w_init_hz) {
        observer.set_ekf_w_init_hz_for_replay(cfg.ekf_w_init_hz);
    }
    if (cfg.has_ekf_pred_time) {
        observer.set_prediction_time_for_replay(cfg.ekf_pred_time);
    }
    if (cfg.has_ekf_axis_gate || cfg.has_ekf_amp_min || cfg.has_ekf_amp_max) {
        printf("Warning: --ekf-axis-gate/--ekf-amp-min/--ekf-amp-max are deprecated and ignored.\n");
    }
    

    // Apply EKF parameter overrides by forcing EKF reinitialization.
    observer.reset_frequency_estimation();
    
    std::ofstream outfile(out_filename);
    // Write header
    outfile << "Time_s,PLX,PLY,PLZ,EstFreq_Hz,EstFreq_X_Hz,EstFreq_Y_Hz,SW,RealSW,DX,DY,VX,VY,CX,CY,PRX,PRY,RealFreq_Hz,RealPhase\n";

    uint32_t start_time_us = data[0].time_us;
    uint32_t prev_time_ms = 0;
    bool have_prev_time = false;
    
    for (const auto& d : data) {
        float rel_time_s = (d.time_us - start_time_us) * 1e-6f;
        uint32_t rel_time_ms = (uint32_t)(rel_time_s * 1000.0f);

        // Guard against duplicate millisecond stamps after float truncation.
        // Duplicate timestamps can yield dt=0 in replay mode and trigger FPE.
        if (have_prev_time && rel_time_ms <= prev_time_ms) {
            rel_time_ms = prev_time_ms + 1;
        }
        prev_time_ms = rel_time_ms;
        have_prev_time = true;
        
        observer.set_replay_time_ms(rel_time_ms);
        
        const bool real_sw = (d.sw != 0);
        bool current_sw = real_sw;
        if (cfg.sw_mode == "always-on") {
            current_sw = true;
        } else if (cfg.sw_mode == "always-off") {
            current_sw = false;
        }
        if (force_window) {
            const float switch_on_s = 20.0f;
            const float settle_delay_s = 10.0f;
            const float window_s = 10.0f;
            const float sample_catchup_s = 0.5f;
            const float window_end_s = switch_on_s + settle_delay_s + window_s + sample_catchup_s;

            current_sw = (rel_time_s >= switch_on_s) && (rel_time_s < window_end_s);
        }


        
        Vector3f payload(d.plx, d.ply, d.plz);
        observer.force_frequency_estimation_update(payload);
        
        Vector3f D = observer.get_harmonic_sin_coeff();
        Vector3f V = observer.get_harmonic_cos_coeff();
        Vector3f C = observer.get_dc_offset();
        Vector3f P = observer.get_predicted_force();
        
        const int sw_out = current_sw ? 1 : 0;
        const int real_sw_out = real_sw ? 1 : 0;
        char buf[400];
        snprintf(buf, sizeof(buf), "%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%d,%d,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f", 
            rel_time_s, d.plx, d.ply, d.plz,
            observer.get_estimated_frequency(),
            observer.get_axis_estimated_frequency(0),  // X axis frequency
            observer.get_axis_estimated_frequency(1),  // Y axis frequency
            sw_out, real_sw_out,
            D.x, D.y, V.x, V.y, C.x, C.y, P.x, P.y,
            d.real_freq, d.real_phase);
        outfile << buf << "\n";
    }
    printf("Finished: %s\n", out_filename);
}

void setup() {
    // No one-time setup needed
}

void loop() {
    ReplayRunConfig cfg;
    if (!parse_replay_args(cfg)) {
        exit(1);
    }

    if (cfg.single_mode) {
        if (!run_single_input_case(cfg)) {
            exit(1);
        }
        exit(0);
    }
    
    const char* files[] = {
        "analysis/replay/data/00000434.csv",
        "analysis/replay/data/00000443.csv",
        "analysis/replay/data/00000444.BIN"
    };
    
    for (const char* f : files) {
        std::string input_path(f);
        const std::string input_base = basename_without_ext(input_path);
        std::string csv_path = input_path;
        std::string output_base = input_base;

        if (ends_with_ignore_case(input_path, ".bin")) {
            csv_path = "analysis/replay/results/" + input_base + "_from_bin.csv";
            output_base = input_base + "_bin";
            if (!convert_bin_to_csv(input_path, csv_path)) {
                continue;
            }
        }

        bool has_extended_columns = false;
        std::vector<ReplayData> data = read_csv(csv_path.c_str(), has_extended_columns);
        if (data.empty()) {
            printf("Failed to read CSV: %s\n", csv_path.c_str());
            continue;
        }
        printf("Read %lu records from %s.\n", data.size(), csv_path.c_str());

        const bool force_window = (input_base == "00000434") && has_extended_columns;
        std::string suffix = force_window ? "_windowed" : "_result";
        std::string out = "analysis/replay/results/" + output_base + suffix + ".csv";

        printf("Running %s (%s)...\n", output_base.c_str(), force_window ? "windowed" : "standard");
        run_case(out.c_str(), data, force_window, cfg);
    }
    
    exit(0);
}

AP_HAL_MAIN();
