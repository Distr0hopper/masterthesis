import { Column, Entity, ManyToOne, PrimaryGeneratedColumn } from 'typeorm';
import { ParameterDirection } from '../enums';
import { Component } from './component.entity';

@Entity('parameters')
export class Parameter {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column()
  name: string;

  @Column()
  cwlType: string;

  @Column({ nullable: true })
  defaultValue: string;

  @Column({ nullable: true })
  description: string;

  @Column({ type: 'enum', enum: ParameterDirection, default: ParameterDirection.INPUT })
  direction: ParameterDirection;

  @ManyToOne(() => Component, (component) => component.parameters, {
    onDelete: 'CASCADE',
  })
  component: Component;
}
