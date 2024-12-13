import grpc
import json
from concurrent import futures
import database_pb2
import database_pb2_grpc
import federation_pb2
import federation_pb2_grpc
import mysql.connector
from mysql.connector import Error
from FederationQuery import FederationQuery
import tenseal as ts

federated_config = {
    'host': '112.4.115.127',
    'port': 3312,
    'database': 'zhx_0001',
    'user': 'zhx_0001',
    'password': 'ARfDhjdBbBmzrMaY'
}


class FederationServiceServicer(federation_pb2_grpc.FederationServiceServicer):
    def __init__(self, config):
        try:
            # 初始化连接和游标
            self.connection = mysql.connector.connect(**config)
            self.cursor = self.connection.cursor()
            # 初始化所属的小型数据库
            self.database_address = self.get_database_address()
            print('Connection successful')
        except Error as e:
            print("Error while connecting to MySQL", e)
        # 初始化查询工具类
        self.context = self.generate_encrypt_context()
        self.querier = FederationQuery(self.database_address, self.context)

    def get_database_address(self):
        try:
            # 定义参数化查询
            query = "SELECT database_address FROM address"
            # 执行查询
            self.cursor.execute(query)
            # 获取查询结果
            records = self.cursor.fetchall()
            results = []
            for record in records:
                results.append(record[0])
            # 返回结果
            return results
        except Error as e:
            print("Error while connecting to MySQL", e)

    @staticmethod
    def generate_encrypt_context():
        context = ts.context(
            ts.SCHEME_TYPE.CKKS,
            poly_modulus_degree=16384,
            coeff_mod_bit_sizes=[60, 40, 40, 60]
        )
        context.generate_galois_keys()
        context.global_scale = 2 ** 40
        return context

    def Check(self, request, context):
        # 接受数据
        query_type = request.query_type
        position_x = request.position_x
        position_y = request.position_y
        query_num = request.query_num
        encrypt = request.encrypt
        results = []
        final_results = []
        if query_type == federation_pb2.Nearest:
            if not encrypt:
                results = self.querier.nearest_query(position_x, position_y, query_num)
            else:
                results = self.querier.encrypted_nearest_query(position_x, position_y, query_num)
        else:
            results = self.querier.anti_nearest_query(position_x, position_y)
        for result in results:
            final_results.append(federation_pb2.CheckResult(
                position_x=result.position_x,
                position_y=result.position_y,
                database_id=result.database_id))

        return federation_pb2.CheckResponse(
            results=final_results,
        )

    def AddDatabase(self, request, context):
        """处理AddDatabase请求"""
        # TODO: 实现函数逻辑
        return federation_pb2.AddResponse()

    def GenerateMap(self, request, context):
        """处理GenerateMap请求"""
        # TODO: 实现函数逻辑
        return federation_pb2.MapResponse()


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    federation_pb2_grpc.add_FederationServiceServicer_to_server(FederationServiceServicer(federated_config), server)
    server.add_insecure_port('[::]:50051')
    print("Server is running on port 50051...")
    server.start()
    server.wait_for_termination()


if __name__ == '__main__':
    serve()
