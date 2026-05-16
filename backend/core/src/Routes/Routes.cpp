#include "Routes.hpp"

namespace check_params
{
    std::string check_symbol(const std::string& s)
    {
        for (const auto coin : CRYPTO)
        {
            if (s == coin) { return s; }
        }
        return "BTCUSDT";
    }


    std::string check_TF(const std::string& tf)
    {
        for (const auto val : TF)
        {
            if (tf == val) { return tf; }
        }
        return "1d";
    }
}


void routes(crow::SimpleApp& app, DbPool& pool)
{
    CROW_ROUTE(app, "/coin/<string>").methods(crow::HTTPMethod::GET)
    ([&pool](const crow::request& req, std::string s)
    {
        const std::string symbol = check_params::check_symbol(s);

        auto tf_param = req.url_params.get("tf");
        const std::string tf = check_params::check_TF(tf_param ? tf_param : "");

        auto offset_param = req.url_params.get("offset");
        int offset = 0;
        if (offset_param) 
        {
            int val = std::atoi(offset_param);
            if (val >= 0) 
            { 
                offset = val; 
                if (offset > LIMITS.at(tf) - 200) { offset = LIMITS.at(tf) - 200; }
            }
        }

        return handlers::get_candles_data(symbol, tf, offset, pool);
    });
}