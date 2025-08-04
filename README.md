# High-Performance Rinha Backend

A highly optimized FastAPI backend for the Rinha de Backend challenge, designed to run efficiently on constrained hardware resources.

## 🚀 Performance Optimizations

### Hardware Constraints
- **API Service**: 0.4 CPU, 1GB RAM
- **Database**: 0.8 CPU, 1.5GB RAM  
- **Redis**: 0.2 CPU, 256MB RAM
- **Nginx**: 0.1 CPU, 256MB RAM

### Key Optimizations Implemented

#### 1. **Database Optimizations**
- **Prepared Statements**: All SQL queries use prepared statements to reduce parsing overhead
- **Optimized Connection Pooling**: Reduced pool sizes to match hardware constraints (5-20 connections)
- **Smart Indexing**: Composite indexes on frequently queried columns
- **PostgreSQL Tuning**: Optimized configuration for 0.8 CPU and 1.5GB RAM

#### 2. **Caching Strategy**
- **Smart Caching**: Separate caches for balance and statements with different TTLs
- **Cache Hit Tracking**: Monitor cache performance with hit/miss statistics
- **Selective Invalidation**: Only invalidate write-related caches, preserve read caches
- **Optimized Serialization**: Use `orjson` for 3x faster JSON serialization

#### 3. **Memory Optimizations**
- **Pydantic Models with `__slots__`**: Reduce memory allocation overhead
- **Connection Pool Optimization**: Minimize memory usage per connection
- **Efficient Data Structures**: Use memory-efficient containers and avoid unnecessary allocations

#### 4. **Async Performance**
- **Concurrent Operations**: Use `asyncio.gather()` for parallel database operations
- **Optimized Error Handling**: Minimize exception overhead in hot paths
- **Connection Reuse**: Efficient connection pooling and reuse

#### 5. **Response Optimizations**
- **GZip Compression**: Compress responses larger than 1KB
- **Optimized JSON**: Use `orjson` for faster serialization
- **Response Caching**: Cache frequently accessed statements

#### 6. **Server Optimizations**
- **Uvicorn Tuning**: Optimized for single worker with async handling
- **Connection Limits**: Limit concurrent connections to prevent resource exhaustion
- **Graceful Shutdown**: Fast shutdown for container orchestration

## 📊 Performance Features

### Monitoring Endpoints
- `/health` - Health check with cache statistics
- `/metrics` - Performance metrics and pool status

### Cache Performance
- Separate caches for balance and statements
- Hit rate tracking and optimization
- Smart invalidation strategies

### Database Performance
- Prepared statements for all queries
- Optimized connection pooling
- Efficient transaction handling with proper locking

## 🛠️ Installation & Usage

### Prerequisites
- Docker and Docker Compose
- Python 3.11+ (for local development)

### Quick Start
```bash
# Start the optimized backend
docker-compose up -d

# Run performance tests
python test_performance.py

# Check health
curl http://localhost:9999/health
```

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py
```

## 📈 Performance Testing

The included `test_performance.py` script provides comprehensive performance testing:

- **Transaction Creation**: Tests write performance
- **Statement Retrieval**: Tests read performance with caching
- **Concurrent Requests**: Tests multi-client scenarios
- **Cache Performance**: Measures cache hit/miss ratios
- **Health Monitoring**: Validates system health

### Running Tests
```bash
python test_performance.py
```

## 🔧 Configuration

### Environment Variables
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `DATABASE_POOL_MIN_SIZE`: Minimum DB connections (default: 5)
- `DATABASE_POOL_MAX_SIZE`: Maximum DB connections (default: 20)
- `REDIS_POOL_SIZE`: Redis connection pool size (default: 10)
- `CACHE_TTL`: Cache time-to-live in seconds (default: 600)

### Hardware-Specific Settings
All configurations are optimized for the specified hardware constraints:
- Reduced connection pools for CPU constraints
- Memory-efficient settings for RAM limits
- Optimized timeouts and buffer sizes

## 🏗️ Architecture

### Components
1. **FastAPI Application**: High-performance async web framework
2. **PostgreSQL Database**: Optimized with prepared statements and indexing
3. **Redis Cache**: Smart caching with hit tracking
4. **Nginx Load Balancer**: Optimized for high throughput
5. **Docker Compose**: Containerized deployment

### Data Flow
1. Request → Nginx (load balancing)
2. Nginx → FastAPI (async processing)
3. FastAPI → Cache (if available)
4. FastAPI → Database (if cache miss)
5. Response → Client (compressed if needed)

## 📋 API Endpoints

### POST `/clientes/{client_id}/transacoes`
Create a new transaction with optimized locking and validation.

**Request:**
```json
{
  "valor": 100,
  "tipo": "c",
  "descricao": "test"
}
```

**Response:**
```json
{
  "limite": 100000,
  "saldo": 100
}
```

### GET `/clientes/{client_id}/extrato`
Get client statement with aggressive caching for read-heavy workloads.

**Response:**
```json
{
  "saldo": {
    "total": 100,
    "data_extrato": "2024-01-01T00:00:00Z",
    "limite": 100000
  },
  "ultimas_transacoes": [...]
}
```

### GET `/health`
Health check with cache performance statistics.

### GET `/metrics`
Performance metrics and system status.

## 🎯 Performance Targets

### Optimized for:
- **High Throughput**: Efficient handling of concurrent requests
- **Low Latency**: Sub-10ms response times for cached requests
- **Memory Efficiency**: Minimal memory footprint for constrained environments
- **CPU Efficiency**: Optimized for 0.4 CPU constraint
- **Cache Hit Rate**: >90% for read-heavy workloads

### Key Metrics:
- **Response Time**: <10ms for cached requests
- **Throughput**: >1000 RPS on specified hardware
- **Memory Usage**: <512MB for API service
- **Cache Hit Rate**: >90% for statements

## 🔍 Monitoring

### Health Checks
- Database connectivity
- Redis connectivity
- Cache performance statistics
- Connection pool status

### Metrics
- Request/response times
- Cache hit/miss ratios
- Database connection pool usage
- Memory usage statistics

## 🚨 Error Handling

- **Graceful Degradation**: System continues operating with reduced performance
- **Connection Retry**: Automatic retry for transient failures
- **Timeout Management**: Optimized timeouts for hardware constraints
- **Error Logging**: Minimal logging for performance

## 📝 License

This project is optimized for the Rinha de Backend challenge and follows best practices for high-performance web applications. 