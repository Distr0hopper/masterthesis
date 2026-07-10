import {
  Column,
  CreateDateColumn,
  Entity,
  JoinColumn,
  ManyToOne,
  OneToMany,
  PrimaryGeneratedColumn,
  Unique,
  UpdateDateColumn,
} from 'typeorm';
import { ComponentDomain, ComponentSource } from '../enums';
import { Parameter } from './parameter.entity';
import { User } from '../../users/entities/user.entity';

@Entity('components')
@Unique(['name', 'version'])
export class Component {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column()
  name: string;

  @Column({ nullable: true })
  authorName: string;

  @ManyToOne(() => User, (user) => user.components, { nullable: true, eager: false })
  @JoinColumn({ name: 'author_id' })
  author: User | null;

  @Column({ nullable: true })
  description: string;

  @Column({ nullable: true })
  repoUrl: string;

  @Column({ nullable: true })
  repoCommitSha: string;

  @Column({ nullable: true })
  doi: string;

  @Column({ type: 'int', default: 1 })
  version: number;

  @Column('text')
  cwlContent: string;

  @Column({ type: 'enum', enum: ComponentSource, default: ComponentSource.MANUAL_UPLOAD })
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