import {
  Column,
  CreateDateColumn,
  Entity,
  OneToMany,
  PrimaryGeneratedColumn,
  Unique,
  UpdateDateColumn,
} from 'typeorm';
import { ComponentDomain, ComponentSource } from '../enums';
import { Parameter } from './parameter.entity';

@Entity('components')
@Unique(['lineageId', 'version'])
export class Component {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column()
  name: string;

  @Column({ nullable: true })
  description: string;

  @Column({ nullable: true })
  repoUrl: string;

  @Column({ nullable: true })
  repoCommitSha: string;

  @Column({ type: 'uuid' })
  lineageId: string;

  @Column({ type: 'int', default: 1 })
  version: number;

  @Column('text')
  cwlContent: string;

  @Column({ type: 'enum', enum: ComponentSource, default: ComponentSource.MANUAL })
  source: ComponentSource;

  @Column({ type: 'varchar' })
  domain: ComponentDomain;

  @OneToMany(() => Parameter, (parameter) => parameter.component, {
    cascade: true,
    eager: true,
  })
  parameters: Parameter[];

  @CreateDateColumn()
  createdAt: Date;

  @UpdateDateColumn()
  updatedAt: Date;
}