import { Controller, Get, InternalServerErrorException } from '@nestjs/common';
import { InjectDataSource } from '@nestjs/typeorm';
import { DataSource } from 'typeorm';

@Controller('health')
export class HealthController {
  constructor(@InjectDataSource() private readonly dataSource: DataSource) {}

  @Get()
  async check() {
    await this.dataSource.query('SELECT 1').catch(() => {
      throw new InternalServerErrorException({ status: 'error', database: 'unreachable' });
    });
    return { status: 'ok', database: 'connected' };
  }
}
