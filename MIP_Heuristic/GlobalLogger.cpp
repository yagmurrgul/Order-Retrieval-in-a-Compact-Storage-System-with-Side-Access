#include "GlobalLogger.h"
#include <iomanip>

std::ofstream GlobalLogger::m_ofs;

void GlobalLogger::Log(const std::string& instance_name, const std::string& runtime, const std::string& obj_val, const std::string& lb, const std::string& gap, const std::string& nb_uls, const std::string& nb_des_uls, const std::string& grid_occ, const std::string& ul_occ, const std::string& node_count, const std::string& root_lp_bound, const std::string& cuts_added, const std::string& time_to_best)
{
    if (m_ofs.is_open()) {
        m_ofs << std::left << std::setw(20) << instance_name
            << std::left << std::setw(20) << std::setprecision(4) << runtime
            << std::left << std::setw(20) << std::setprecision(0) << obj_val
            << std::left << std::setw(20) << std::setprecision(0) << lb
            << std::left << std::setw(20) << std::setprecision(4) << gap
            << std::left << std::setw(20) << std::setprecision(2) << nb_uls
            << std::left << std::setw(20) << std::setprecision(2) << nb_des_uls
            << std::left << std::setw(20) << std::setprecision(2) << grid_occ
            << std::left << std::setw(20) << std::setprecision(2) << ul_occ
            << std::left << std::setw(20) << node_count
            << std::left << std::setw(20) << root_lp_bound
            << std::left << std::setw(20) << cuts_added
            << std::left << std::setw(20) << time_to_best
            << std::endl;
    }
}
