#include "Threads.hpp"

namespace sync_data
{
    void threads(const std::vector<std::string>& TF, const std::vector<std::string>& CRYPTO, DbPool& history_pool)
    {
        for (const auto& symbol : CRYPTO) 
        {
            std::thread([&history_pool, TF, symbol]() 
            {
                std::cout << "[History Synchronization for " << symbol << "] started" << std::endl;
                {
                    DbPool::ConnGuard connection_guard = history_pool.get_guard();
                        
                    for (const auto& tf : TF)
                    {
                        data_stream::fetch_and_save_candles(symbol, tf, connection_guard);
                    }
                }
                std::cout << "[History Synchronization for " << symbol << " ] finished" << std::endl;
            }).detach();
        }
    }
}