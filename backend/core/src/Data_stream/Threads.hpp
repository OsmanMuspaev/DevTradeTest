#pragma once
#include <iostream>
#include <thread>
#include <chrono>
#include "../DB_pool.hpp"
#include "History_data.hpp"


namespace sync_data
{
    void threads(const std::vector<std::string>& TF, const std::vector<std::string>& CRYPTO, DbPool& history_pool);
}