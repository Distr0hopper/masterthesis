import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { Component } from './entities/component.entity';
import { Parameter } from './entities/parameter.entity';

@Injectable()
export class ComponentsService {
  constructor(
    @InjectRepository(Component)
    private readonly componentRepo: Repository<Component>,
    @InjectRepository(Parameter)
    private readonly parameterRepo: Repository<Parameter>,
  ) {}

  // createManual and packageFromUrl will be implemented in Phase 3
}
