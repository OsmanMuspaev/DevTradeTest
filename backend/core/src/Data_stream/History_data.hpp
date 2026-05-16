#pragma once
#define CPPHTTPLIB_OPENSSL_SUPPORT
#include <httplib.h>
#include <json.hpp>
#include "../DB_pool.hpp"
#include "../config.hpp"
#include <pqxx/pqxx>
#include <iostream>


namespace data_stream
{
    void fetch_and_save_candles(const std::string& symbol, const std::string& tf, DbPool::ConnGuard& connection_guard);
}