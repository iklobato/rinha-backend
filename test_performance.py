#!/usr/bin/env python3
"""
Performance testing script for the optimized Rinha backend
Tests various scenarios to validate performance optimizations
"""

import asyncio
import aiohttp
import time
import statistics
from typing import List, Dict, Any
import json


class PerformanceTester:
    def __init__(self, base_url: str = "http://localhost:9999"):
        self.base_url = base_url
        self.results: Dict[str, List[float]] = {}
    
    async def test_transaction_creation(self, client_id: int, num_requests: int = 100) -> List[float]:
        """Test transaction creation performance"""
        times = []
        
        async with aiohttp.ClientSession() as session:
            for i in range(num_requests):
                start_time = time.time()
                
                payload = {
                    "valor": 100,
                    "tipo": "c" if i % 2 == 0 else "d",
                    "descricao": f"test{i}"
                }
                
                async with session.post(
                    f"{self.base_url}/clientes/{client_id}/transacoes",
                    json=payload
                ) as response:
                    await response.json()
                
                times.append(time.time() - start_time)
        
        return times
    
    async def test_statement_retrieval(self, client_id: int, num_requests: int = 100) -> List[float]:
        """Test statement retrieval performance"""
        times = []
        
        async with aiohttp.ClientSession() as session:
            for _ in range(num_requests):
                start_time = time.time()
                
                async with session.get(
                    f"{self.base_url}/clientes/{client_id}/extrato"
                ) as response:
                    await response.json()
                
                times.append(time.time() - start_time)
        
        return times
    
    async def test_concurrent_requests(self, num_clients: int = 5, requests_per_client: int = 20) -> List[float]:
        """Test concurrent request performance"""
        times = []
        
        async def client_work(client_id: int):
            client_times = []
            async with aiohttp.ClientSession() as session:
                for i in range(requests_per_client):
                    start_time = time.time()
                    
                    # Alternate between transaction and statement
                    if i % 2 == 0:
                        payload = {
                            "valor": 50,
                            "tipo": "c",
                            "descricao": f"concurrent{i}"
                        }
                        async with session.post(
                            f"{self.base_url}/clientes/{client_id}/transacoes",
                            json=payload
                        ) as response:
                            await response.json()
                    else:
                        async with session.get(
                            f"{self.base_url}/clientes/{client_id}/extrato"
                        ) as response:
                            await response.json()
                    
                    client_times.append(time.time() - start_time)
            return client_times
        
        # Run concurrent clients
        tasks = [client_work(client_id) for client_id in range(1, num_clients + 1)]
        results = await asyncio.gather(*tasks)
        
        # Flatten results
        for client_times in results:
            times.extend(client_times)
        
        return times
    
    async def test_cache_performance(self, client_id: int = 1) -> Dict[str, Any]:
        """Test cache performance by measuring response times"""
        # First request (cache miss)
        start_time = time.time()
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/clientes/{client_id}/extrato") as response:
                await response.json()
        cache_miss_time = time.time() - start_time
        
        # Second request (cache hit)
        start_time = time.time()
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/clientes/{client_id}/extrato") as response:
                await response.json()
        cache_hit_time = time.time() - start_time
        
        return {
            "cache_miss_time": cache_miss_time,
            "cache_hit_time": cache_hit_time,
            "cache_improvement": (cache_miss_time - cache_hit_time) / cache_miss_time * 100
        }
    
    def calculate_stats(self, times: List[float]) -> Dict[str, float]:
        """Calculate performance statistics"""
        return {
            "count": len(times),
            "mean": statistics.mean(times),
            "median": statistics.median(times),
            "min": min(times),
            "max": max(times),
            "std_dev": statistics.stdev(times) if len(times) > 1 else 0,
            "p95": sorted(times)[int(len(times) * 0.95)] if times else 0,
            "p99": sorted(times)[int(len(times) * 0.99)] if times else 0
        }
    
    async def run_full_test(self):
        """Run comprehensive performance test"""
        print("🚀 Starting Performance Test Suite")
        print("=" * 50)
        
        # Test 1: Transaction Creation
        print("\n📝 Testing Transaction Creation (100 requests)...")
        transaction_times = await self.test_transaction_creation(1, 100)
        self.results["transaction_creation"] = transaction_times
        stats = self.calculate_stats(transaction_times)
        print(f"   Mean: {stats['mean']:.4f}s")
        print(f"   P95: {stats['p95']:.4f}s")
        print(f"   P99: {stats['p99']:.4f}s")
        
        # Test 2: Statement Retrieval
        print("\n📊 Testing Statement Retrieval (100 requests)...")
        statement_times = await self.test_statement_retrieval(1, 100)
        self.results["statement_retrieval"] = statement_times
        stats = self.calculate_stats(statement_times)
        print(f"   Mean: {stats['mean']:.4f}s")
        print(f"   P95: {stats['p95']:.4f}s")
        print(f"   P99: {stats['p99']:.4f}s")
        
        # Test 3: Concurrent Requests
        print("\n⚡ Testing Concurrent Requests (5 clients, 20 requests each)...")
        concurrent_times = await self.test_concurrent_requests(5, 20)
        self.results["concurrent_requests"] = concurrent_times
        stats = self.calculate_stats(concurrent_times)
        print(f"   Mean: {stats['mean']:.4f}s")
        print(f"   P95: {stats['p95']:.4f}s")
        print(f"   P99: {stats['p99']:.4f}s")
        
        # Test 4: Cache Performance
        print("\n💾 Testing Cache Performance...")
        cache_stats = await self.test_cache_performance(1)
        print(f"   Cache Miss: {cache_stats['cache_miss_time']:.4f}s")
        print(f"   Cache Hit: {cache_stats['cache_hit_time']:.4f}s")
        print(f"   Improvement: {cache_stats['cache_improvement']:.1f}%")
        
        # Test 5: Health Check
        print("\n🏥 Testing Health Check...")
        start_time = time.time()
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/health") as response:
                health_data = await response.json()
        health_time = time.time() - start_time
        print(f"   Health Check Time: {health_time:.4f}s")
        print(f"   Cache Stats: {health_data.get('cache_stats', {})}")
        
        # Summary
        print("\n" + "=" * 50)
        print("📈 PERFORMANCE SUMMARY")
        print("=" * 50)
        
        total_requests = sum(len(times) for times in self.results.values())
        total_time = sum(sum(times) for times in self.results.values())
        avg_rps = total_requests / total_time if total_time > 0 else 0
        
        print(f"Total Requests: {total_requests}")
        print(f"Total Time: {total_time:.2f}s")
        print(f"Average RPS: {avg_rps:.2f}")
        
        # Save results
        with open("performance_results.json", "w") as f:
            json.dump({
                "results": self.results,
                "summary": {
                    "total_requests": total_requests,
                    "total_time": total_time,
                    "avg_rps": avg_rps
                }
            }, f, indent=2)
        
        print(f"\n💾 Results saved to performance_results.json")


async def main():
    """Main test runner"""
    tester = PerformanceTester()
    await tester.run_full_test()


if __name__ == "__main__":
    asyncio.run(main()) 