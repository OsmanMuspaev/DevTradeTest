cmake_minimum_required(VERSION 3.10)
project(app)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

include_directories(include)

find_package(Crow CONFIG REQUIRED)
find_package(libpqxx CONFIG REQUIRED)
find_package(OpenSSL REQUIRED)
find_package(ixwebsocket CONFIG REQUIRED)
find_package(ZLIB REQUIRED)
find_package(hiredis CONFIG REQUIRED)
find_package(redis++ CONFIG REQUIRED)

add_executable(app 
    src/main.cpp
    src/Routes/Routes.cpp
    src/Handlers/Candles_data.cpp
    src/Data_stream/History_data.cpp
    src/Data_stream/Live_data.cpp
    src/Data_stream/Threads.cpp
)

target_compile_options(app PRIVATE -w)

target_link_libraries(app
    PRIVATE 
        Crow::Crow
        libpqxx::pqxx
        OpenSSL::SSL 
        OpenSSL::Crypto
        ixwebsocket::ixwebsocket
        ZLIB::ZLIB
        hiredis::hiredis
        ${redis++_LIBRARIES}
)


# CI TEST
enable_testing()

add_executable(core_tests 
    tests/Test.cpp
    src/Data_stream/Live_data.cpp
    src/Routes/Routes.cpp
    src/Handlers/Candles_data.cpp
) 

target_compile_options(core_tests PRIVATE -w)

target_link_libraries(core_tests 
    PRIVATE 
        Crow::Crow
        libpqxx::pqxx
        OpenSSL::SSL 
        OpenSSL::Crypto
        ixwebsocket::ixwebsocket
        ZLIB::ZLIB
        hiredis::hiredis
        ${redis++_LIBRARIES}
)

add_test(NAME CoreLogicTest COMMAND core_tests)