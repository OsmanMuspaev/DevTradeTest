#pragma once
#include <crow.h>
#include <pqxx/pqxx>
#include "../DB_pool.hpp"


namespace handlers 
{
    crow::response get_candles_data(const std::string& symbol, const std::string& tf, const int offset, DbPool& pool);
}