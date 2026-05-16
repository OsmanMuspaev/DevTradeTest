#pragma once
#include <iostream>
#include <unordered_map>
#include <fstream>
#include <json.hpp>
#include <vector>
#include <string>


inline const std::string RESET = "\033[0m";
inline const std::string RED = "\033[31m";
inline const std::string GREEN = "\033[32m";
inline const std::string YELLOW = "\033[33m";

inline std::vector<std::string> CRYPTO;
inline std::vector<std::string> TF;
inline std::unordered_map<std::string, int> LIMITS;

namespace config
{
    inline void init_data()
    {
        std::ifstream p("params.json");
        if (!p.is_open()) 
        {
            std::cout << RED << "Could not open params.json" << RESET << std::endl;
            return;
        }

        try
        {
        nlohmann::json params = nlohmann::json::parse(p);

        auto crypto_list = params["crypto_list"].get<std::vector<std::string>>();
        for(const auto& c : crypto_list) { CRYPTO.push_back(c); }

        auto timeframes = params["timeframes"].get<std::vector<std::string>>();
        for(const auto& t : timeframes) { TF.push_back(t); }

        LIMITS = params["candles_amount"].get<std::unordered_map<std::string, int>>();
        }
        catch(const std::exception &err)
        {
            std::cout << RED << err.what() << RESET << std::endl;
        }
    }
}