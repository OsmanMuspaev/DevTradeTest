#pragma once
#include <crow.h>
#include "../DB_pool.hpp"
#include "../Handlers/Candles_data.hpp"
#include "../config.hpp"

namespace check_params
{
    std::string check_symbol(const std::string& s);

    std::string check_TF(const std::string& tf);
}

void routes(crow::SimpleApp& app, DbPool& pool);