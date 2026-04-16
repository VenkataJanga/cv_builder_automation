import asyncio

from src.core.logging.logger import get_logger


logger = get_logger(__name__)

async def main():
    logger.info('Worker started')
    await asyncio.sleep(0.1)

if __name__ == '__main__':
    asyncio.run(main())
