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
        data.push_back(d);
    }
    return data;
}

static void run_case(float alpha, const char* out_filename, const std::vector<ReplayData>& data) {
    // Reset observer by reconstruction
    new (&observer) AP_Observer();
    observer.set_replay_time_ms(0); // Ensure time starts at 0 for init
    observer.init();
    // 初期化後にパラメータを上書き
    observer.set_params_for_replay(0.5794f, 20.0f, 0.0f);
    observer.set_freq_est_alpha(alpha);
    
    if (AP_Param::set_by_name("OBS_RLS_LAMBDA", 0.99f)) {} 
    if (AP_Param::set_by_name("OBS_RLS_COV_INIT", 100.0f)) {} 
    if (AP_Param::set_by_name("OBS_PHASE_CORR", 1.0f)) {}
    if (AP_Param::set_by_name("OBS_CORR_GAIN", 0.0f)) {}
    
    std::ofstream outfile(out_filename);
    // Write header
    outfile << "Time_s,PLX,PLY,EstFreq_Hz,PhaseCorr,SW,RealSW,RLS_A_X,RLS_B_X\n";

    uint32_t start_time_us = data[0].time_us;
    
    for (const auto& d : data) {
        float rel_time_s = (d.time_us - start_time_us) * 1e-6f;
        uint32_t rel_time_ms = (uint32_t)(rel_time_s * 1000.0f);
        
        observer.set_replay_time_ms(rel_time_ms);
        
        // Use recorded switch state
        bool current_sw = (d.sw != 0);
        static bool prev_sw = false;

        // Reset frequency estimation on OFF -> ON transition
        if (current_sw && !prev_sw) {
             observer.reset_frequency_estimation();
        }
        prev_sw = current_sw;

        observer.set_freq_estimation_active(current_sw);
        
        Vector3f payload(d.plx, d.ply, d.plz);
        observer.force_rls_update(payload);
        
        Vector3f A = observer.get_rls_sin_coeff();
        Vector3f B = observer.get_rls_cos_coeff();
        
        char buf[256];
        snprintf(buf, sizeof(buf), "%.4f,%.4f,%.4f,%.4f,%.4f,%d,%d,%.4f,%.4f", 
               rel_time_s, d.plx, d.ply, 
               observer.get_estimated_frequency(), 
               observer.get_phase_correction(),
               d.sw, d.sw,
               A.x, B.x);
        outfile << buf << "\n";
    }
    printf("Finished: %s (Alpha=%.2f)\n", out_filename, alpha);
}

void setup() {
    // No one-time setup needed
}

void loop() {
    std::string csv_path = "analysis/replay/data/replay_data.csv";
    std::vector<ReplayData> data = read_csv(csv_path.c_str());
    if (data.empty()) {
        printf("Failed to read CSV\n");
        exit(1);
    }
    printf("Read %lu records.\n", data.size());
    
    // Run Alpha=0.05
    run_case(0.05f, "analysis/replay/results/result.csv", data);
    
    // Run Alpha=0.01
    run_case(0.01f, "analysis/replay/results/result_alpha001.csv", data);
    
    exit(0);
}

AP_HAL_MAIN();
