#include "History_data.hpp"


namespace data_stream
{
    void fetch_and_save_candles(const std::string& symbol, const std::string& tf, DbPool::ConnGuard& connection_guard)
    {
        try
        {
            int target_limit{};
            try 
            {
                target_limit = LIMITS.at(tf);
            } 
            catch (const std::out_of_range& e) 
            {
                std::cerr << RED << "Timeframe " << tf << " not found" << RESET << std::endl;
                target_limit = 1000;
            }

            std::string api_url = "/api/v3/klines?symbol=" + symbol + "&interval=" + tf;
            {
                pqxx::nontransaction read_data(*connection_guard);
                pqxx::result r = read_data.exec_params(
                    "SELECT MAX(open_time) "
                    "FROM crypto_candles WHERE symbol = $1 AND time_frame = $2", 
                    symbol, tf
                );

                if (!r.empty() && !r[0][0].is_null()) 
                {
                    long long last_time_ms = r[0][0].as<long long>() * 1000;
                    api_url += "&startTime=" + std::to_string(last_time_ms);

                    std::cout << YELLOW << "Checking " << symbol << " " << tf << " From " << last_time_ms << " ms" << RESET << std::endl;
                } 
                else 
                {
                    std::cout << YELLOW << symbol << " " << tf << " is empty | starting sync process" << RESET << std::endl;
                    api_url += "&limit=1000";
                }
            }
            


            httplib::Client client("https://api.binance.com");
            auto res = client.Get(api_url);
            if (res && res->status == 200) 
            {
                nlohmann::json candles_data = nlohmann::json::parse(res->body);
                if (!candles_data.empty()) 
                { 
                    pqxx::work write_data(*connection_guard);
                    for (const auto& item : candles_data) 
                    {
                        long long open_time = item[0].get<long long>() / 1000;
                        double open_price = std::stod(item[1].get<std::string>());
                        double high_price = std::stod(item[2].get<std::string>());
                        double low_price = std::stod(item[3].get<std::string>());
                        double close_price = std::stod(item[4].get<std::string>());
                        double volume = std::stod(item[5].get<std::string>());
                        bool is_grow = close_price - open_price >= 0 ? true : false;

                        write_data.exec_params(
                            "INSERT INTO crypto_candles (symbol, time_frame, open_time, open_price, high_price, low_price, close_price, volume, is_grow) "
                            "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9) "
                            "ON CONFLICT (symbol, time_frame, open_time) DO UPDATE SET "
                            "   high_price = GREATEST(crypto_candles.high_price, EXCLUDED.high_price), "
                            "   low_price = LEAST(crypto_candles.low_price, EXCLUDED.low_price), "
                            "   close_price = EXCLUDED.close_price, "
                            "   volume = EXCLUDED.volume, "
                            "   is_grow = EXCLUDED.is_grow",
                            symbol, tf, open_time, open_price, high_price, low_price, close_price, volume, is_grow
                        );
                    }
                    write_data.commit();
                }
            }
            else
            {
                throw std::runtime_error("Binance: " + std::to_string(res->status) + " " + res->body);
            }



            while (true) 
            {
                long long current_count = 0;
                long long oldest_time = 0;
                {
                    pqxx::nontransaction check_db(*connection_guard);
                    auto count_res = check_db.exec_params(
                        "SELECT COUNT(*) FROM crypto_candles WHERE symbol = $1 AND time_frame = $2", symbol, tf);
                    current_count = count_res[0][0].as<long long>();

                    auto min_res = check_db.exec_params(
                        "SELECT MIN(open_time) "
                        "FROM crypto_candles WHERE symbol = $1 AND time_frame = $2", symbol, tf);

                    if (!min_res.empty() && !min_res[0][0].is_null()) 
                    {
                        oldest_time = min_res[0][0].as<long long>();
                    }
                }

                if (current_count >= target_limit || oldest_time == 0) { break; }

                std::cout << YELLOW << "History Sync: " << symbol << " " << tf << " | Current: " 
                          << current_count << "/" << target_limit << " | Fetching before " 
                          << oldest_time << "sec" << RESET << std::endl;

                std::string history_url = "/api/v3/klines?symbol=" + symbol + "&interval=" + tf + 
                                       "&limit=1000&endTime=" + std::to_string((oldest_time * 1000) - 1);
                
                auto h_res = client.Get(history_url);
                if (!h_res || h_res->status != 200) { break; }

                nlohmann::json history_data = nlohmann::json::parse(h_res->body);
                if (history_data.empty()) { break; }

                pqxx::work write_history(*connection_guard);
                for (const auto& item : history_data) 
                {
                    long long open_time = item[0].get<long long>() / 1000;
                    double open_price = std::stod(item[1].get<std::string>());
                    double high_price = std::stod(item[2].get<std::string>());
                    double low_price = std::stod(item[3].get<std::string>());
                    double close_price = std::stod(item[4].get<std::string>());
                    double volume = std::stod(item[5].get<std::string>());
                    bool is_grow = close_price - open_price >= 0 ? true : false;

                    write_history.exec_params(
                        "INSERT INTO crypto_candles (symbol, time_frame, open_time, open_price, high_price, low_price, close_price, volume, is_grow) "
                        "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9) "
                        "ON CONFLICT (symbol, time_frame, open_time) DO NOTHING",
                        symbol, tf, open_time, open_price, high_price, low_price, close_price, volume, is_grow
                    );
                }
                write_history.commit();

                std::this_thread::sleep_for(std::chrono::milliseconds(100));
            }

            std::cout << GREEN << symbol << " " << tf << " Updated" << RESET << std::endl;
        }
        catch(const std::exception& e)
        {
            std::cerr << "Sync error: " << e.what() << std::endl;
        }
    }
}