#pragma once
#include <pqxx/pqxx>
#include <json.hpp>
#include <ixwebsocket/IXWebSocket.h>
#include "../DB_pool.hpp"
#include "../config.hpp"
#include <mutex>
#include <map>
#include <chrono>
#include <thread>

std::string set_streams(const std::vector<std::string>& CRYPTO, const std::vector<std::string>& TF);

void live_data_update(const std::vector<std::string>& CRYPTO, const std::vector<std::string>& TF, DbPool& pool);