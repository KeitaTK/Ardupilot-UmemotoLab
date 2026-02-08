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

static std::vector<ReplayData> read_csv(const char* filename) {
    std::vector<ReplayData> data;
    std::ifstream file(filename);
    std::string line;
    
    // Skip header
    std::getline(file, line);
    
    while (std::getline(file, line)) {
        if (line.empty()) continue;
        std::stringstream ss(line);
        std::string item;
        ReplayData d;
        
        if (std::getline(ss, item, ',')) d.time_us = strtoul(item.c_str(), nullptr, 10);
        if (std::getline(ss, item, ',')) d.plx = strtof(item.c_str(), nullptr);
        if (std::getline(ss, item, ',')) d.ply = strtof(item.c_str(), nullptr);
        if (std::getline(ss, item, ',')) d.plz = strtof(item.c_str(), nullptr);
        if (std::getline(ss, item, ',')) d.sw = strtol(item.c_str(), nullptr, 10);
        if (std::getline(ss, item, ',')) d.real_freq = strtof(item.c_str(), nullptr);
        if (std::getline(ss, item, ',')) d.real_phase = strtof(item.c_str(), nullptr);
        data.push_back(d);
    }
    return data;
}

static void run_case(const char* out_filename, const std::vector<ReplayData>& data, bool force_window) {
    // Reset observer by reconstruction
    new (&observer) AP_Observer();
    observer.set_replay_time_ms(0); // Ensure time starts at 0 for init
    observer.init();
    // 初期化後にパラメータを上書き
    // Ensure start frequency matches 0.74m equivalent (0.5794Hz)
    // Code should converge to 1.04m equivalent (0.488Hz) if data supports it
    observer.set_params_for_replay(0.5794f, 20.0f, 0.0f);
    
    if (AP_Param::set_by_name("OBS_RLS_LAMBDA", 0.99f)) {} 
    if (AP_Param::set_by_name("OBS_RLS_COV_INIT", 100.0f)) {} 
    if (AP_Param::set_by_name("OBS_PHASE_CORR", 1.0f)) {}
    if (AP_Param::set_by_name("OBS_CORR_GAIN", 0.0f)) {}
    if (AP_Param::set_by_name("OBS_FREQ_WIN", 10.0f)) {}
    
    std::ofstream outfile(out_filename);
    // Write header
    outfile << "Time_s,PLX,PLY,EstFreq_Hz,PhaseCorr,SW,RealSW,RLS_A_X,RLS_B_X,RealFreq_Hz,RealPhase\n";

    uint32_t start_time_us = data[0].time_us;
    
    for (const auto& d : data) {
        float rel_time_s = (d.time_us - start_time_us) * 1e-6f;
        uint32_t rel_time_ms = (uint32_t)(rel_time_s * 1000.0f);
        
        observer.set_replay_time_ms(rel_time_ms);
        
            bool current_sw = (d.sw != 0);
            bool estimation_sw = current_sw;
            if (force_window) {
                const float switch_on_s = 20.0f;
                const float settle_delay_s = 10.0f;
                const float window_s = 10.0f;
                const float sample_catchup_s = 0.5f;
                const float window_start_s = switch_on_s + settle_delay_s;
                const float window_end_s = window_start_s + window_s + sample_catchup_s;

                current_sw = (rel_time_s >= switch_on_s) && (rel_time_s < window_end_s);
                estimation_sw = (rel_time_s >= window_start_s) && (rel_time_s < window_end_s);
            }

            observer.set_freq_estimation_active(estimation_sw);
        
        Vector3f payload(d.plx, d.ply, d.plz);
        observer.force_rls_update(payload);
        
        Vector3f A = observer.get_rls_sin_coeff();
        Vector3f B = observer.get_rls_cos_coeff();
        
         const int sw_out = current_sw ? 1 : 0;
         char buf[256];
         snprintf(buf, sizeof(buf), "%.4f,%.4f,%.4f,%.4f,%.4f,%d,%d,%.4f,%.4f,%.4f,%.4f", 
             rel_time_s, d.plx, d.ply, 
             observer.get_estimated_frequency(), 
             observer.get_phase_correction(),
             sw_out, sw_out,
             A.x, B.x,
             d.real_freq, d.real_phase);
        outfile << buf << "\n";
    }
    printf("Finished: %s\n", out_filename);
}

void setup() {
    // No one-time setup needed
}

void loop() {
    // Check command line arguments
    // Usage: ./RLS_CSV_Replay <csv_path> <alpha> <output_path>
    // If no args, run default behavior (loop over files and fixed alphas)
    
    // In ArduPilot examples, accessing raw argc/argv isn't standard in loop(), 
    // but for Linux port (SITL), we can access global args or just assume this IS main on some platforms.
    // However, AP_HAL_MAIN uses a specific entry.
    // Let's rely on hardcoded loop for now if we can't get args easily without changing HAL.
    // Wait, SITL allows passing args?
    // Usually not through to the sketch easily.
    
    // Instead of args, I will just iterate my sweep list here directly.
    
    const char* files[] = {
        "analysis/replay/data/00000434.csv",
        "analysis/replay/data/00000443.csv",
        "analysis/replay/data/00000444.csv"
    };
    
    for (const char* f : files) {
        std::vector<ReplayData> data = read_csv(f);
        if (data.empty()) {
            printf("Failed to read CSV: %s\n", f);
            continue;
        }
        printf("Read %lu records from %s.\n", data.size(), f);

        std::string base = f; 
        size_t lastslash = base.find_last_of("/");
        if (lastslash != std::string::npos) base = base.substr(lastslash+1);
        base = base.substr(0, base.size()-4); // remove .csv

           const bool force_window = (base == "00000434");
           std::string suffix = force_window ? "_zero_cross" : "_result";
           std::string out = "analysis/replay/results/" + base + suffix + ".csv";

           printf("Running %s (%s)...\n", base.c_str(), force_window ? "zero-cross" : "standard");
           run_case(out.c_str(), data, force_window);
    }
    
    exit(0);
}

AP_HAL_MAIN();
