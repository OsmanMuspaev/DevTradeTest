#include <iostream>
#include <cassert>
#include "../src/Data_stream/Live_data.hpp"
#include "../src/Routes/Routes.hpp"

int main() {
    std::cout << "==========RUNNING CORE TESTS==========" << std::endl;

    assert(set_streams({"BTCUSDT"}, {"1m", "5m"}) == "btcusdt@kline_1m/btcusdt@kline_5m");

    assert(check_params::check_symbol("ETHUSDT") == "ETHUSDT");
    assert(check_params::check_symbol("INVALID") == "BTCUSDT");

    assert(check_params::check_TF("1m") == "1m");
    assert(check_params::check_TF("INVALID") == "1d");

    std::cout << "==========ALL TESTS PASSED==========" << std::endl;
    return 0;
}