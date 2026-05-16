#pragma once
#include <pqxx/pqxx>
#include <memory>
#include <mutex>
#include <queue>
#include <condition_variable>
#include <string>


class DbPool 
{
private:
    std::queue<std::unique_ptr<pqxx::connection>> connections;
    std::mutex mtx;
    std::condition_variable cond_var;

public:
    DbPool(const std::string& connection_string, size_t pool_size) 
    {
        for (size_t i = 0; i < pool_size; ++i) {

            connections.push(std::make_unique<pqxx::connection>(connection_string));
        }
    }

    std::unique_ptr<pqxx::connection> acquire() 
    {
        std::unique_lock<std::mutex> lock(mtx);
        
        cond_var.wait(lock, [this](){ return !connections.empty(); });
        
        auto conn = std::move(connections.front());
        connections.pop();
        return conn;
    }

    void release(std::unique_ptr<pqxx::connection> conn) 
    {
        std::lock_guard<std::mutex> lock(mtx);
        connections.push(std::move(conn));
        cond_var.notify_one();
    }



    class ConnGuard 
    {
    private:
        DbPool& pool;
        std::unique_ptr<pqxx::connection> conn;

    public:
        ConnGuard(DbPool& p) : pool(p), conn(p.acquire()) {}
        
        ~ConnGuard() { if (conn) { pool.release(std::move(conn)); } }

        pqxx::connection* operator->() { return conn.get(); }
        pqxx::connection& operator*() { return *conn; }

        ConnGuard(const ConnGuard&) = delete;
        ConnGuard& operator=(const ConnGuard&) = delete;
    };

    ConnGuard get_guard() { return ConnGuard(*this); }
};