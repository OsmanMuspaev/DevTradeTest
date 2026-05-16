#include "Candles_data.hpp"

namespace handlers
{
    crow::response get_candles_data(const std::string& symbol, const std::string& tf, const int offset, DbPool& pool)
    {
        try 
        {
            DbPool::ConnGuard connection_guard2 = pool.get_guard();

            if (!connection_guard2->is_open()) 
            {
                return crow::response(500, "Database connection lost");
            }

            pqxx::nontransaction read_data(*connection_guard2);
            pqxx::result r = read_data.exec_params(
                "SELECT open_time, "
                "open_price, high_price, low_price, close_price, volume, is_grow "
                "FROM crypto_candles "
                "WHERE symbol = $1 AND time_frame = $2 "
                "ORDER BY open_time DESC "
                "LIMIT 200 OFFSET $3",
                symbol, tf, offset
            );

            crow::json::wvalue response_data{};
            std::vector<crow::json::wvalue> candles{};

            for (const auto& row : r) 
            {
                crow::json::wvalue candle;
                candle["open_time"]   = row[0].as<long long>();
                candle["open_price"]  = row[1].as<double>();
                candle["high_price"]  = row[2].as<double>();
                candle["low_price"]   = row[3].as<double>();
                candle["close_price"] = row[4].as<double>();
                candle["volume"]      = row[5].as<double>();
                candle["is_grow"]     = row[6].as<bool>();

                candles.push_back(std::move(candle));
            }
            
            response_data["symbol"] = symbol;
            response_data["time_frame"] = tf;
            response_data["data"] = std::move(candles);

            return crow::response(response_data);
        } 
        catch (const std::exception& e) 
        {
            return crow::response(500, std::string("Error: ") + e.what());
        }
    }
}