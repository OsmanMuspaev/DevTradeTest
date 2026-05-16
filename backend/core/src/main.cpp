#include <crow.h>
#include <pqxx/pqxx>
#include "config.hpp"
#include "DB_pool.hpp"
#include "Routes/Routes.hpp"
#include "Data_stream/Live_data.hpp"
#include "Data_stream/Threads.hpp"


int main() 
{
    const std::string db_url = std::getenv("DB_URL");
    if (db_url.empty()) 
    {
        std::cerr << "DB_URL is not set" << std::endl;
        return 1;
    }
    config::init_data();

    DbPool pool(db_url, std::min(static_cast<int>(CRYPTO.size()) + 20, 50));
    live_data_update(CRYPTO, TF, pool);

    sync_data::threads(TF, CRYPTO, pool);

    crow::SimpleApp app{};
    routes(app, pool);
    app.port(18080).concurrency(6).run();

    return 0;
}