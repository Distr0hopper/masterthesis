import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { ComponentsController } from './components.controller';
import { ComponentsService } from './components.service';
import { Component } from './entities/component.entity';
import { Parameter } from './entities/parameter.entity';

@Module({
  imports: [TypeOrmModule.forFeature([Component, Parameter])],
  controllers: [ComponentsController],
  providers: [ComponentsService],
  exports: [ComponentsService],
})
export class ComponentsModule {}
