#include "Live_data.hpp"

struct CandleUpdate 
{
    std::string s, tf;
    long long t;
    double o, h, l, c, v;
    bool is_grow;
};

static std::map<std::string, CandleUpdate> candle_buffer;
static std::mutex buffer_mutex;
const char* env_ms = std::getenv("LIVE_INTERVAL_MS");


static void clean_old_data(DbPool& pool)
{
    while(true)
    {
        std::this_thread::sleep_for(std::chrono::minutes(5));

        auto now = std::chrono::system_clock::now();
        auto limit_365_days = std::chrono::system_clock::to_time_t(now - std::chrono::hours(24 * 365));
        auto limit_7_days   = std::chrono::system_clock::to_time_t(now - std::chrono::hours(24 * 7));
        auto limit_1_hour   = std::chrono::system_clock::to_time_t(now - std::chrono::hours(1));

        DbPool::ConnGuard connection_guard_clean = pool.get_guard();
        pqxx::work work_clean(*connection_guard_clean);

        work_clean.exec_params("DELETE FROM crypto_candles WHERE time_frame IN ('1h', '4h') AND open_time < $1", limit_365_days);
        work_clean.exec_params("DELETE FROM crypto_candles WHERE time_frame IN ('5m', '15m') AND open_time < $1", limit_7_days);
        work_clean.exec_params("DELETE FROM crypto_candles WHERE time_frame IN ('1m', '1s') AND open_time < $1", limit_1_hour);
        
        work_clean.commit();
    }
}


static void flush_buffer_to_db(DbPool& pool) 
{
    static const unsigned int LIVE_INTERVAL_MS = env_ms ? std::stoi(env_ms) : 1000;
    while (true) 
    {
        std::this_thread::sleep_for(std::chrono::milliseconds(LIVE_INTERVAL_MS));

        std::map<std::string, CandleUpdate> local_copy;
        {
            std::lock_guard<std::mutex> lock(buffer_mutex);
            if (candle_buffer.empty()) { continue; }
            candle_buffer.swap(local_copy);
        }

        DbPool::ConnGuard connection_guard_live = pool.get_guard();
        pqxx::work work_live(*connection_guard_live);
        for (auto const& [key, data] : local_copy) 
        {
            work_live.exec_params(
                "INSERT INTO crypto_candles (symbol, time_frame, open_time, open_price, high_price, low_price, close_price, volume, is_grow) "
                "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9) "
                "ON CONFLICT (symbol, time_frame, open_time) DO UPDATE SET "
                "   close_price = EXCLUDED.close_price, "
                "   high_price = GREATEST(crypto_candles.high_price, EXCLUDED.high_price), "
                "   low_price = LEAST(crypto_candles.low_price, EXCLUDED.low_price), "
                "   volume = EXCLUDED.volume, "
                "   is_grow = EXCLUDED.is_grow",
                data.s, data.tf, data.t, data.o, data.h, data.l, data.c, data.v, data.is_grow
            );
        }
        work_live.commit();
    }
}


std::string set_streams(const std::vector<std::string>& CRYPTO, const std::vector<std::string>& TF)
{
    // btcusdt@kline_5m/btcusdt@kline_1h/ethusdt@kline_5m...
    std::string streams = "";
    
    for (auto coin : CRYPTO) 
    {
        std::transform(coin.begin(), coin.end(), coin.begin(), ::tolower);

        for (const auto& tf : TF) 
        {
            streams += coin + "@kline_" + tf + "/";
        }
    }
    streams.pop_back(); 

    return streams;
}


void live_data_update(const std::vector<std::string>& CRYPTO, const std::vector<std::string>& TF, DbPool& pool) 
{
    static ix::WebSocket webSocket;

    static std::thread flusher([&pool]() { flush_buffer_to_db(pool); });
    flusher.detach();
    static std::thread cleaner([&pool]() { clean_old_data(pool); });
    cleaner.detach();


    webSocket.setUrl("wss://stream.binance.com:9443/stream?streams=" + set_streams(CRYPTO, TF));

    webSocket.enableAutomaticReconnection();

    webSocket.setOnMessageCallback([&pool](const ix::WebSocketMessagePtr& msg) 
    {
        if (msg->type == ix::WebSocketMessageType::Message) 
        {
            auto json = nlohmann::json::parse(msg->str);
            auto& k = json["data"]["k"]; 

            CandleUpdate update{
                k["s"], 
                k["i"], 
                k["t"].get<long long>() / 1000,
                std::stod(k["o"].get<std::string>()),
                std::stod(k["h"].get<std::string>()),
                std::stod(k["l"].get<std::string>()),
                std::stod(k["c"].get<std::string>()),
                std::stod(k["v"].get<std::string>()),
                false
            };
            update.is_grow = (update.c >= update.o);

            std::string key = update.s + "_" + update.tf + "_" + std::to_string(update.t);
            {
                std::lock_guard<std::mutex> lock(buffer_mutex);
                candle_buffer[key] = update; 
            }
        }
    });
    webSocket.start();
}